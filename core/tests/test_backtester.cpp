#include "backtester.h"
#include "order_flat_fee.h"
#include "percentage_fee.h"
#include "share_flat_fee.h"
#include "sma_strategy.h"
#include "strategy.h"
#include <gtest/gtest.h>
#include <memory>
#include <vector>

namespace {

class ScriptedStrategy : public Strategy {
public:
  struct Action {
    std::int64_t timestamp;
    int side;
    int quantity;
  };

  std::vector<Action> actions;
  std::vector<std::int64_t> seen_timestamps;

  explicit ScriptedStrategy(std::vector<Action> actions)
      : actions(std::move(actions)) {}

  std::vector<Order> on_bar(const Bar &bar,
                            const Portfolio & /*portfolio*/) override {
    seen_timestamps.push_back(bar.timestamp);
    std::vector<Order> orders;
    for (const auto &act : actions) {
      if (act.timestamp == bar.timestamp) {
        orders.push_back(Order{bar.ticker, bar.timestamp, act.quantity,
                               bar.close, act.side});
      }
    }
    return orders;
  }

  int get_warmup_days() const override { return 0; }
};

Bar make_bar(const std::string &ticker, std::int64_t ts, double price) {
  return Bar{ticker, ts, price, price + 1.0, price - 1.0, price, 5000.0};
}

} // namespace

TEST(BacktesterTest, EmptyAndAllWarmupBarsReturnEmptyCurves) {
  auto fee = std::make_shared<OrderFlatFee>(0.0);
  auto strat = std::make_shared<SMAStrategy>(1000, 4, 2);

  Backtester bt_empty(10000.0, strat, 1000, fee);
  bt_empty.run({});
  EXPECT_TRUE(bt_empty.get_equity_curve().empty());
  EXPECT_TRUE(bt_empty.get_timestamps().empty());

  std::vector<Bar> warmup_only = {make_bar("AAPL", 100, 10.0),
                                  make_bar("AAPL", 200, 12.0)};
  Backtester bt_warmup(10000.0, strat, 1000, fee);
  bt_warmup.run(warmup_only);
  EXPECT_TRUE(bt_warmup.get_equity_curve().empty());
  EXPECT_TRUE(bt_warmup.get_timestamps().empty());
}

TEST(BacktesterTest, EventLoopExecutionAndEndLiquidation) {
  auto fee = std::make_shared<OrderFlatFee>(0.0);
  auto strat =
      std::make_shared<ScriptedStrategy>(std::vector<ScriptedStrategy::Action>{
          {200, 1, 10},
          {300, 1, 5},
      });

  std::vector<Bar> bars = {
      make_bar("AAPL", 100, 90.0), // warmup
      make_bar("AAPL", 200, 100.0),
      make_bar("MSFT", 300, 200.0),
      make_bar("AAPL", 400, 120.0),
      make_bar("MSFT", 500, 180.0),
  };

  Backtester bt(5000.0, strat, 200, fee);
  bt.run(bars);

  const auto &equity = bt.get_equity_curve();
  const auto &ts = bt.get_timestamps();
  const auto &portfolio = bt.get_portfolio();

  ASSERT_EQ(equity.size(), ts.size());
  // initial + 4 bars + liquidation
  ASSERT_EQ(equity.size(), 6);
  EXPECT_EQ(ts.front(), 199);
  EXPECT_EQ(ts[1], 200);
  EXPECT_EQ(ts[4], 500);
  EXPECT_EQ(ts.back(), 501);

  EXPECT_DOUBLE_EQ(equity[0], 5000.0);
  EXPECT_DOUBLE_EQ(equity[1], 5000.0);
  EXPECT_DOUBLE_EQ(equity[2], 5000.0);
  EXPECT_DOUBLE_EQ(equity[3], 5200.0);
  EXPECT_DOUBLE_EQ(equity[4], 5100.0);
  EXPECT_DOUBLE_EQ(equity[5], 5100.0);

  EXPECT_TRUE(portfolio.get_positions().empty());
  EXPECT_DOUBLE_EQ(portfolio.get_cash(), 5100.0);
  EXPECT_EQ(portfolio.get_trade_history().size(), 2);
}

TEST(BacktesterTest, AbsenceOfLookAheadBias) {
  auto fee = std::make_shared<PercentageFee>(0.001, 0.0, 0.0);

  std::vector<Bar> prefix_bars = {
      make_bar("AAPL", 1, 10.0), make_bar("AAPL", 2, 10.0),
      make_bar("AAPL", 3, 10.0), make_bar("AAPL", 4, 10.0),
      make_bar("AAPL", 5, 20.0), make_bar("AAPL", 6, 22.0),
  };

  // Divergent future bars must not affect ticks <= 6
  std::vector<Bar> extended_crash = prefix_bars;
  extended_crash.push_back(make_bar("AAPL", 7, 1.0));
  extended_crash.push_back(make_bar("AAPL", 8, 500.0));

  std::vector<Bar> extended_rally = prefix_bars;
  extended_rally.push_back(make_bar("AAPL", 7, 200.0));
  extended_rally.push_back(make_bar("AAPL", 8, 300.0));

  auto strat1 = std::make_shared<SMAStrategy>(1, 4, 2);
  auto strat2 = std::make_shared<SMAStrategy>(1, 4, 2);
  auto strat3 = std::make_shared<SMAStrategy>(1, 4, 2);

  Backtester bt_prefix(10000.0, strat1, 1, fee);
  Backtester bt_crash(10000.0, strat2, 1, fee);
  Backtester bt_rally(10000.0, strat3, 1, fee);

  bt_prefix.run(prefix_bars);
  bt_crash.run(extended_crash);
  bt_rally.run(extended_rally);

  ASSERT_GE(bt_prefix.get_equity_curve().size(), 7);
  for (size_t i = 0; i <= 6; ++i) {
    EXPECT_DOUBLE_EQ(bt_crash.get_equity_curve()[i],
                     bt_prefix.get_equity_curve()[i]);
    EXPECT_DOUBLE_EQ(bt_rally.get_equity_curve()[i],
                     bt_prefix.get_equity_curve()[i]);
    EXPECT_EQ(bt_crash.get_timestamps()[i], bt_prefix.get_timestamps()[i]);
  }

  ASSERT_FALSE(bt_crash.get_portfolio().get_trade_history().empty());
  ASSERT_FALSE(bt_rally.get_portfolio().get_trade_history().empty());
  EXPECT_EQ(bt_crash.get_portfolio().get_trade_history()[0].entry_time, 5);
  EXPECT_EQ(bt_rally.get_portfolio().get_trade_history()[0].entry_time, 5);
  EXPECT_DOUBLE_EQ(bt_crash.get_portfolio().get_trade_history()[0].entry_price,
                   20.0);
  EXPECT_DOUBLE_EQ(bt_rally.get_portfolio().get_trade_history()[0].entry_price,
                   20.0);
}

TEST(BacktesterTest, FeeDeductionAccuracyAcrossMultipleTrades) {
  auto fee = std::make_shared<ShareFlatFee>(0.10, 1.0, 20.0);
  auto strat =
      std::make_shared<ScriptedStrategy>(std::vector<ScriptedStrategy::Action>{
          {10, 1, 50},
          {20, -1, 50},
          {30, 1, 5},
          {40, -1, 5},
      });

  std::vector<Bar> bars = {
      make_bar("AAPL", 10, 100.0),
      make_bar("AAPL", 20, 110.0),
      make_bar("AAPL", 30, 110.0),
      make_bar("AAPL", 40, 100.0),
  };

  Backtester bt(10000.0, strat, 10, fee);
  bt.run(bars);

  const auto &trades = bt.get_portfolio().get_trade_history();
  ASSERT_EQ(trades.size(), 2);

  EXPECT_DOUBLE_EQ(trades[0].realized_pnl, 500.0);
  EXPECT_DOUBLE_EQ(trades[0].fee_paid, 10.0);
  EXPECT_EQ(trades[0].entry_time, 10);
  EXPECT_EQ(trades[0].exit_time, 20);
  EXPECT_EQ(trades[0].side, 1);

  EXPECT_DOUBLE_EQ(trades[1].realized_pnl, -50.0);
  EXPECT_DOUBLE_EQ(trades[1].fee_paid, 2.0);

  double total_pnl = 0.0;
  double total_fees = 0.0;
  for (const auto &t : trades) {
    total_pnl += t.realized_pnl;
    total_fees += t.fee_paid;
  }

  EXPECT_DOUBLE_EQ(bt.get_portfolio().get_cash(),
                   10000.0 + total_pnl - total_fees);
  EXPECT_DOUBLE_EQ(bt.get_equity_curve().back(), 10000.0 + 450.0 - 12.0);
}
