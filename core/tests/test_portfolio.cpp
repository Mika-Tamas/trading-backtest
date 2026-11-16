#include "order_flat_fee.h"
#include "percentage_fee.h"
#include "portfolio.h"
#include "share_flat_fee.h"
#include <gtest/gtest.h>

TEST(PortfolioTest, Initialization) {
  auto fee = std::make_shared<ShareFlatFee>(0.01, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  EXPECT_DOUBLE_EQ(p.get_cash(), 10000.0);
  EXPECT_EQ(p.get_positions().size(), 0);
}

TEST(PortfolioTest, ExecuteBuyOrder) {
  auto fee = std::make_shared<ShareFlatFee>(0.0, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  Order order{"AAPL", 1600000000, 10, 150.0, 1};
  p.execute_order(order);

  EXPECT_DOUBLE_EQ(p.get_cash(), 10000.0 - 1500.0);

  auto positions = p.get_positions();
  ASSERT_TRUE(positions.find("AAPL") != positions.end());
  EXPECT_EQ(positions.at("AAPL").quantity, 10);
  EXPECT_DOUBLE_EQ(positions.at("AAPL").average_entry_price, 150.0);
}

TEST(PortfolioTest, ExecuteSellOrder) {
  auto fee = std::make_shared<ShareFlatFee>(0.0, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  Order buy{"AAPL", 1600000000, 10, 150.0, 1};
  p.execute_order(buy);

  Order sell{"AAPL", 1600001000, 5, 160.0, -1};
  p.execute_order(sell);

  EXPECT_DOUBLE_EQ(p.get_cash(), 8500.0 + 800.0);

  auto positions = p.get_positions();
  EXPECT_EQ(positions.at("AAPL").quantity, 5);

  auto trades = p.get_trade_history();
  ASSERT_EQ(trades.size(), 1);
  EXPECT_EQ(trades[0].quantity, 5);
  EXPECT_DOUBLE_EQ(trades[0].realized_pnl, 50.0);
}

TEST(PortfolioTest, EquityCalculation) {
  auto fee = std::make_shared<ShareFlatFee>(0.0, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  Order buy{"AAPL", 1600000000, 10, 150.0, 1};
  p.execute_order(buy);

  std::unordered_map<std::string, double> prices;
  prices["AAPL"] = 160.0;

  EXPECT_DOUBLE_EQ(p.get_equity(prices), 10100.0);
}

TEST(PortfolioTest, InsufficientCashRejectionIncludesFees) {
  auto fee = std::make_shared<OrderFlatFee>(10.0);
  Portfolio p(fee, 1000.0);

  // Rejected due to fee ($1000 + $10 > $1000)
  p.execute_order(Order{"AAPL", 100, 10, 100.0, 1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 1000.0);
  EXPECT_TRUE(p.get_positions().empty());
  EXPECT_TRUE(p.get_trade_history().empty());

  p.execute_order(Order{"AAPL", 101, 50, 100.0, 1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 1000.0);
  EXPECT_EQ(p.get_position_quantity("AAPL"), 0);

  p.execute_order(Order{"AAPL", 102, 9, 100.0, 1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 90.0);
  EXPECT_EQ(p.get_position_quantity("AAPL"), 9);

  p.execute_order(Order{"AAPL", 103, 1, 100.0, 1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 90.0);
  EXPECT_EQ(p.get_position_quantity("AAPL"), 9);
}

TEST(PortfolioTest, PartialVsFullLiquidationAndFeeSplitting) {
  auto fee = std::make_shared<OrderFlatFee>(10.0);
  Portfolio p(fee, 5000.0);

  p.execute_order(Order{"AAPL", 100, 10, 100.0, 1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 3990.0);

  // Partial sell 4/10: entry fee 4 + close fee 10 = 14
  p.execute_order(Order{"AAPL", 200, 4, 120.0, -1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 4460.0);
  EXPECT_EQ(p.get_position_quantity("AAPL"), 6);
  ASSERT_EQ(p.get_trade_history().size(), 1);
  EXPECT_DOUBLE_EQ(p.get_trade_history()[0].realized_pnl, 80.0);
  EXPECT_DOUBLE_EQ(p.get_trade_history()[0].fee_paid, 14.0);

  p.execute_order(Order{"AAPL", 300, 6, 110.0, -1});
  EXPECT_DOUBLE_EQ(p.get_cash(), 5110.0);
  EXPECT_TRUE(p.get_positions().empty());
  ASSERT_EQ(p.get_trade_history().size(), 2);
  EXPECT_DOUBLE_EQ(p.get_trade_history()[1].realized_pnl, 60.0);
  EXPECT_DOUBLE_EQ(p.get_trade_history()[1].fee_paid, 16.0);

  // No double-counting across split closes
  double total_fees =
      p.get_trade_history()[0].fee_paid + p.get_trade_history()[1].fee_paid;
  EXPECT_DOUBLE_EQ(total_fees, 30.0);
}

TEST(PortfolioTest, ReversalAndRealizedUnrealizedPnLAcrossPriceSwings) {
  auto fee = std::make_shared<PercentageFee>(0.01, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  p.execute_order(Order{"AAPL", 10, 10, 100.0, 1});
  p.execute_order(Order{"AAPL", 20, 10, 120.0, 1});
  EXPECT_EQ(p.get_position_quantity("AAPL"), 20);
  EXPECT_DOUBLE_EQ(p.get_positions().at("AAPL").average_entry_price, 110.0);

  EXPECT_DOUBLE_EQ(p.get_equity({{"AAPL", 150.0}}), 10778.0);
  EXPECT_DOUBLE_EQ(p.get_equity({{"AAPL", 90.0}}), 9578.0);
  // Falls back to avg entry price
  EXPECT_DOUBLE_EQ(p.get_equity({}), 7778.0 + 20 * 110.0);

  // Reverse 20 long -> 10 short; remaining fee = 39 * (10/30)
  p.execute_order(Order{"AAPL", 30, 30, 130.0, -1});
  EXPECT_EQ(p.get_position_quantity("AAPL"), -10);
  EXPECT_DOUBLE_EQ(p.get_positions().at("AAPL").average_entry_price, 130.0);
  EXPECT_DOUBLE_EQ(p.get_positions().at("AAPL").fee_paid, 13.0);

  ASSERT_EQ(p.get_trade_history().size(), 1);
  EXPECT_DOUBLE_EQ(p.get_trade_history()[0].realized_pnl, 400.0);
  EXPECT_DOUBLE_EQ(p.get_trade_history()[0].fee_paid, 48.0);

  double cash_after_reverse = p.get_cash();
  EXPECT_DOUBLE_EQ(cash_after_reverse, 11639.0);
  EXPECT_DOUBLE_EQ(p.get_equity({{"AAPL", 100.0}}), 11639.0 - 1000.0);
  EXPECT_DOUBLE_EQ(p.get_equity({{"AAPL", 150.0}}), 11639.0 - 1500.0);

  // Underwater short cover allowed
  Portfolio underwater(std::make_shared<OrderFlatFee>(0.0), 1000.0);
  underwater.execute_order(Order{"AAPL", 1, 10, 100.0, -1});
  underwater.execute_order(Order{"AAPL", 2, 10, 250.0, 1});
  EXPECT_TRUE(underwater.get_positions().empty());
  EXPECT_DOUBLE_EQ(underwater.get_cash(), -500.0);
}
