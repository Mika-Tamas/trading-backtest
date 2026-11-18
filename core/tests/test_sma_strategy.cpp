#include "order_flat_fee.h"
#include "percentage_fee.h"
#include "portfolio.h"
#include "share_flat_fee.h"
#include "sma_strategy.h"
#include <cmath>
#include <gtest/gtest.h>
#include <memory>
#include <numeric>
#include <string>
#include <utility>
#include <vector>

namespace {

Bar make_bar(const std::string &ticker, std::int64_t ts, double close) {
  return Bar{ticker, ts, close, close, close, close, 1000.0};
}

} // namespace

TEST(SMAStrategyTest, NormalizesSwappedPeriodsAndReportsWarmupDays) {
  SMAStrategy strat(1000, /*slow=*/3, /*fast=*/7);
  EXPECT_EQ(strat.get_warmup_days(), 7);
}

TEST(SMAStrategyTest, WarmupSuppressesSignalsBeforeSlowWindowAndTimestamp) {
  auto fee = std::make_shared<OrderFlatFee>(0.0);
  Portfolio portfolio(fee, 10000.0);
  SMAStrategy strat(100, 4, 2);

  EXPECT_TRUE(strat.on_bar(make_bar("AAPL", 101, 10.0), portfolio).empty());
  EXPECT_TRUE(strat.on_bar(make_bar("AAPL", 102, 10.0), portfolio).empty());
  EXPECT_TRUE(strat.on_bar(make_bar("AAPL", 103, 10.0), portfolio).empty());

  // Needs >= 2 SMA points to detect cross
  EXPECT_TRUE(strat.on_bar(make_bar("AAPL", 104, 50.0), portfolio).empty());

  // Timestamp-gated warmup
  SMAStrategy gated(500, 4, 2);
  std::vector<double> prices = {10.0, 10.0, 10.0, 10.0, 50.0, 60.0};
  for (size_t i = 0; i < prices.size(); ++i) {
    auto orders = gated.on_bar(
        make_bar("AAPL", 100 + static_cast<int>(i), prices[i]), portfolio);
    EXPECT_TRUE(orders.empty());
  }
}

TEST(SMAStrategyTest, GoldenCrossAndDeathCrossExactSignals) {
  auto fee = std::make_shared<OrderFlatFee>(0.0);
  Portfolio portfolio(fee, 1000.0);
  SMAStrategy strat(1, 4, 2);

  for (int t = 1; t <= 4; ++t) {
    ASSERT_TRUE(strat.on_bar(make_bar("AAPL", t, 10.0), portfolio).empty());
  }

  // Golden cross: fast 10->15 crosses slow 10->12.5
  auto buy_orders = strat.on_bar(make_bar("AAPL", 5, 20.0), portfolio);
  ASSERT_EQ(buy_orders.size(), 1);
  EXPECT_EQ(buy_orders[0].ticker, "AAPL");
  EXPECT_EQ(buy_orders[0].side, 1);
  EXPECT_EQ(buy_orders[0].quantity, 50);
  EXPECT_DOUBLE_EQ(buy_orders[0].price, 20.0);
  EXPECT_EQ(buy_orders[0].timestamp, 5);
  portfolio.execute_order(buy_orders[0]);

  EXPECT_TRUE(strat.on_bar(make_bar("AAPL", 6, 20.0), portfolio).empty());
  EXPECT_TRUE(strat.on_bar(make_bar("AAPL", 7, 20.0), portfolio).empty());
  // Death cross: fast 20->15 crosses slow 17.5->17.5; closes 50 long + opens 50 short
  auto sell_orders = strat.on_bar(make_bar("AAPL", 8, 10.0), portfolio);
  ASSERT_EQ(sell_orders.size(), 1);
  EXPECT_EQ(sell_orders[0].side, -1);
  EXPECT_DOUBLE_EQ(sell_orders[0].price, 10.0);
  EXPECT_EQ(sell_orders[0].quantity, 100);
}

TEST(SMAStrategyTest, FlatAndOscillatingSeriesAndMultiTickerIsolation) {
  auto fee = std::make_shared<OrderFlatFee>(0.0);
  Portfolio portfolio(fee, 10000.0);
  SMAStrategy flat_strat(1, 5, 2);

  for (int t = 1; t <= 30; ++t) {
    EXPECT_TRUE(
        flat_strat.on_bar(make_bar("FLAT", t, 42.0), portfolio).empty());
  }

  SMAStrategy osc_strat(1, 4, 2);
  Portfolio osc_portfolio(fee, 10000.0);
  std::vector<double> osc = {10, 10, 10, 10, 12, 12, 10, 10, 12, 12, 10, 10};
  int buys = 0;
  int sells = 0;
  for (size_t i = 0; i < osc.size(); ++i) {
    auto orders = osc_strat.on_bar(
        make_bar("OSC", static_cast<int>(i) + 1, osc[i]), osc_portfolio);
    for (const auto &o : orders) {
      if (o.side == 1)
        buys++;
      if (o.side == -1)
        sells++;
      osc_portfolio.execute_order(o);
    }
  }
  EXPECT_GE(buys, 2);
  EXPECT_GE(sells, 2);

  // Multi-ticker isolation
  SMAStrategy multi(1, 4, 2);
  Portfolio multi_portfolio(fee, 10000.0);
  for (int t = 1; t <= 4; ++t) {
    multi.on_bar(make_bar("AAPL", t, 100.0), multi_portfolio);
  }
  EXPECT_TRUE(
      multi.on_bar(make_bar("MSFT", 5, 200.0), multi_portfolio).empty());
}

TEST(SMAStrategyTest, LongStreamKahanSummationMatchesNaiveReference) {
  auto fee = std::make_shared<OrderFlatFee>(0.0);
  const int slow = 20;
  const int fast = 5;
  SMAStrategy strat(1, slow, fast);

  std::vector<double> history;
  double prev_naive_fast = 0.0;
  double prev_naive_slow = 0.0;
  int crossover_count = 0;

  for (int t = 1; t <= 5000; ++t) {
    double price = 100.0 + 15.0 * std::sin(t * 0.03) + 0.001 * t;
    history.push_back(price);
    // Fresh portfolio isolates signal accuracy from equity depletion
    Portfolio probe_portfolio(fee, 100000.0);
    auto orders = strat.on_bar(make_bar("SYN", t, price), probe_portfolio);

    if (static_cast<int>(history.size()) >= slow) {
      double naive_fast =
          std::accumulate(history.end() - fast, history.end(), 0.0) / fast;
      double naive_slow =
          std::accumulate(history.end() - slow, history.end(), 0.0) / slow;

      if (static_cast<int>(history.size()) >= slow + 1) {
        bool golden =
            (prev_naive_fast <= prev_naive_slow) && (naive_fast > naive_slow);
        bool death =
            (prev_naive_fast >= prev_naive_slow) && (naive_fast < naive_slow);
        if (golden) {
          ASSERT_EQ(orders.size(), 1) << "Expected golden cross at t=" << t;
          EXPECT_EQ(orders[0].side, 1);
          crossover_count++;
        } else if (death) {
          ASSERT_EQ(orders.size(), 1) << "Expected death cross at t=" << t;
          EXPECT_EQ(orders[0].side, -1);
          crossover_count++;
        } else {
          EXPECT_TRUE(orders.empty()) << "Unexpected order at t=" << t;
        }
      }
      prev_naive_fast = naive_fast;
      prev_naive_slow = naive_slow;
    }
  }
  EXPECT_GT(crossover_count, 20);
}

TEST(SMAStrategyTest, MultiCycleReversalsWithPercentageAndShareFees) {
  const std::vector<std::pair<std::string, std::shared_ptr<FeeStructure>>> fees = {
      {"PercentageFee", std::make_shared<PercentageFee>(0.01, 1.0, 50.0)},
      {"ShareFlatFee", std::make_shared<ShareFlatFee>(0.05, 1.0, 50.0)},
  };

  for (const auto &[name, fee] : fees) {
    SCOPED_TRACE(name);
    Portfolio portfolio(fee, 10000.0);
    SMAStrategy strat(1, 4, 2);

    // Warmup (t=1..4)
    for (int t = 1; t <= 4; ++t) {
      EXPECT_TRUE(
          strat.on_bar(make_bar("AAPL", t, 10.0), portfolio).empty());
    }

    // Golden Cross #1 (t=5..7)
    int buy1_count = 0;
    for (int t = 5; t <= 7; ++t) {
      auto orders = strat.on_bar(make_bar("AAPL", t, 12.0), portfolio);
      for (const auto &o : orders) {
        EXPECT_EQ(o.side, 1);
        portfolio.execute_order(o);
        buy1_count++;
      }
    }
    ASSERT_EQ(buy1_count, 1);
    EXPECT_GT(portfolio.get_position_quantity("AAPL"), 0);

    // Death Cross #1 (t=8..11)
    int sell1_count = 0;
    for (int t = 8; t <= 11; ++t) {
      auto orders = strat.on_bar(make_bar("AAPL", t, 8.0), portfolio);
      for (const auto &o : orders) {
        EXPECT_EQ(o.side, -1);
        portfolio.execute_order(o);
        sell1_count++;
      }
    }
    ASSERT_EQ(sell1_count, 1);
    EXPECT_LT(portfolio.get_position_quantity("AAPL"), 0);

    // Golden Cross #2 (t=12..15): Short-to-Long reversal must not be rejected
    int buy2_count = 0;
    for (int t = 12; t <= 15; ++t) {
      auto orders = strat.on_bar(make_bar("AAPL", t, 13.0), portfolio);
      for (const auto &o : orders) {
        EXPECT_EQ(o.side, 1);
        portfolio.execute_order(o);
        buy2_count++;
      }
    }
    ASSERT_EQ(buy2_count, 1);
    EXPECT_GT(portfolio.get_position_quantity("AAPL"), 0);
  }
}
