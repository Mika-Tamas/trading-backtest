#include "../../fees/include/Share_flat_fee.h"
#include "Portfolio.h"
#include <gtest/gtest.h>

TEST(PortfolioTest, Initialization) {
  auto fee = std::make_shared<Share_flat_fee>(0.01, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  EXPECT_DOUBLE_EQ(p.get_cash(), 10000.0);
  EXPECT_EQ(p.get_positions().size(), 0);
}

TEST(PortfolioTest, ExecuteBuyOrder) {
  auto fee = std::make_shared<Share_flat_fee>(0.0, 0.0, 0.0);
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
  auto fee = std::make_shared<Share_flat_fee>(0.0, 0.0, 0.0);
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
  auto fee = std::make_shared<Share_flat_fee>(0.0, 0.0, 0.0);
  Portfolio p(fee, 10000.0);

  Order buy{"AAPL", 1600000000, 10, 150.0, 1};
  p.execute_order(buy);

  std::unordered_map<std::string, double> prices;
  prices["AAPL"] = 160.0;

  EXPECT_DOUBLE_EQ(p.get_equity(prices), 10100.0);
}
