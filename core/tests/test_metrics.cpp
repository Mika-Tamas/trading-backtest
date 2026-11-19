#include "metrics.h"
#include <cmath>
#include <gtest/gtest.h>
#include <vector>

namespace {

std::vector<Trade> make_sample_trades() {
  return {
      {"AAPL", 100, 200, 100.0, 110.0, 10, 1, 100.0, 2.0},
      {"AAPL", 300, 400, 110.0, 105.0, 10, 1, -50.0, 2.0},
      {"AAPL", 500, 600, 105.0, 115.0, 10, 1, 100.0, 2.0},
  };
}

void expect_all_finite(Metrics &m) {
  EXPECT_TRUE(std::isfinite(m.get_total_return()));
  EXPECT_TRUE(std::isfinite(m.get_annualized_return()));
  EXPECT_TRUE(std::isfinite(m.get_sharpe_ratio()));
  EXPECT_TRUE(std::isfinite(m.get_sortino_ratio()));
  EXPECT_TRUE(std::isfinite(m.get_information_ratio()));
  EXPECT_TRUE(std::isfinite(m.get_maximum_drawdown()));
  EXPECT_TRUE(std::isfinite(m.get_calmar_ratio()));
  EXPECT_TRUE(std::isfinite(m.get_profit_factor()));
  EXPECT_TRUE(std::isfinite(m.get_win_rate()));
  EXPECT_TRUE(std::isfinite(m.get_beta()));
  EXPECT_TRUE(std::isfinite(m.get_alpha()));
}

} // namespace

TEST(MetricsTest, HandCalculatedRatiosAndTradeMetrics) {
  // Returns: [+0.1, -0.1, +0.1, +0.1]
  std::vector<double> equity = {100.0, 110.0, 99.0, 108.9, 119.79};
  // Benchmark: 0.5x strategy returns
  std::vector<double> benchmark = {100.0, 105.0, 99.75, 104.7375, 109.974375};
  // 0.0001 daily rf
  std::vector<double> rf = {2.52, 2.52, 2.52, 2.52, 2.52};
  std::vector<Trade> trades = make_sample_trades();

  Metrics m(equity, trades, benchmark, rf);

  const double expected_sharpe =
      ((0.05 - 0.0001) / std::sqrt(0.0075)) * std::sqrt(252.0);
  const double expected_sortino =
      ((0.05 - 0.0001) / 0.05005) * std::sqrt(252.0);
  const double expected_ir =
      (0.025 / std::sqrt(0.001875)) * std::sqrt(252.0);
  const double expected_ann_ret =
      (std::pow(1.1979, 252.0 / 5.0) - 1.0) * 100.0;

  EXPECT_NEAR(m.get_total_return(), 19.79, 1e-6);
  EXPECT_NEAR(m.get_annualized_return(), expected_ann_ret, 1e-4);
  EXPECT_NEAR(m.get_sharpe_ratio(), expected_sharpe, 1e-6);
  EXPECT_NEAR(m.get_sortino_ratio(), expected_sortino, 1e-6);
  EXPECT_NEAR(m.get_information_ratio(), expected_ir, 1e-6);
  EXPECT_NEAR(m.get_maximum_drawdown(), 10.0, 1e-6);
  EXPECT_NEAR(m.get_calmar_ratio(), expected_ann_ret / 10.0, 1e-4);
  EXPECT_NEAR(m.get_beta(), 2.0, 1e-6);
  EXPECT_NEAR(m.get_alpha(), 2.52, 1e-6);
  EXPECT_NEAR(m.get_profit_factor(), 200.0 / 50.0, 1e-6);
  EXPECT_NEAR(m.get_win_rate(), (2.0 / 3.0) * 100.0, 1e-6);
}

TEST(MetricsTest, FlatEquityCurveNoDivisionByZeroOrNaN) {
  std::vector<double> flat = {1000.0, 1000.0, 1000.0, 1000.0};
  std::vector<double> bench = {1000.0, 1010.0, 1020.0, 1030.0};
  std::vector<double> rf_zero = {0.0, 0.0, 0.0, 0.0};
  std::vector<double> rf_pos = {2.52, 2.52, 2.52, 2.52};

  Metrics flat_zero_rf(flat, {}, bench, rf_zero);
  expect_all_finite(flat_zero_rf);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_total_return(), 0.0);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_annualized_return(), 0.0);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_sharpe_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_sortino_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_maximum_drawdown(), 0.0);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_calmar_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(flat_zero_rf.get_beta(), 0.0);

  Metrics flat_pos_rf(flat, {}, bench, rf_pos);
  expect_all_finite(flat_pos_rf);
  EXPECT_DOUBLE_EQ(flat_pos_rf.get_sharpe_ratio(), 0.0);
  EXPECT_NEAR(flat_pos_rf.get_sortino_ratio(), -std::sqrt(252.0), 1e-6);

  Metrics flat_vs_flat(flat, {}, flat, rf_zero);
  expect_all_finite(flat_vs_flat);
  EXPECT_DOUBLE_EQ(flat_vs_flat.get_information_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(flat_vs_flat.get_beta(), 0.0);
}

TEST(MetricsTest, IdenticalStrategyAndBenchmarkZeroTrackingError) {
  std::vector<double> curve = {100.0, 110.0, 105.0, 120.0};
  std::vector<double> rf = {0.0, 0.0, 0.0, 0.0};

  Metrics m(curve, {}, curve, rf);
  expect_all_finite(m);
  EXPECT_NEAR(m.get_beta(), 1.0, 1e-9);
  EXPECT_NEAR(m.get_alpha(), 0.0, 1e-9);
  EXPECT_DOUBLE_EQ(m.get_information_ratio(), 0.0);
}

TEST(MetricsTest, MonotonicallyIncreasingReturnsZeroDrawdown) {
  std::vector<double> increasing = {100.0, 105.0, 110.25, 115.7625, 121.550625};
  std::vector<double> bench = {100.0, 101.0, 102.01, 103.0301, 104.060401};
  std::vector<double> rf = {0.0, 0.0, 0.0, 0.0, 0.0};

  Metrics m(increasing, {}, bench, rf);
  expect_all_finite(m);
  EXPECT_DOUBLE_EQ(m.get_maximum_drawdown(), 0.0);
  EXPECT_DOUBLE_EQ(m.get_calmar_ratio(), 999.0);
  EXPECT_DOUBLE_EQ(m.get_sortino_ratio(), 0.0);
  EXPECT_GT(m.get_total_return(), 20.0);
}

TEST(MetricsTest, MonotonicallyDecreasingReturns) {
  std::vector<double> decreasing = {100.0, 90.0, 81.0, 72.9};
  std::vector<double> bench = {100.0, 102.0, 101.0, 104.0};
  std::vector<double> rf = {0.0, 0.0, 0.0, 0.0};

  Metrics m(decreasing, {}, bench, rf);
  expect_all_finite(m);
  EXPECT_NEAR(m.get_total_return(), -27.1, 1e-6);
  EXPECT_NEAR(m.get_maximum_drawdown(), 27.1, 1e-6);
  EXPECT_LT(m.get_sortino_ratio(), 0.0);
  EXPECT_LT(m.get_calmar_ratio(), 0.0);
}

TEST(MetricsTest, SingleElementAndEmptyInputs) {
  Metrics single({1000.0}, {}, {1000.0}, {2.0});
  expect_all_finite(single);
  EXPECT_DOUBLE_EQ(single.get_total_return(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_annualized_return(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_sharpe_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_sortino_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_information_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_maximum_drawdown(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_calmar_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_beta(), 0.0);
  EXPECT_DOUBLE_EQ(single.get_alpha(), 0.0);

  Metrics empty_all({}, {}, {}, {});
  expect_all_finite(empty_all);
  EXPECT_DOUBLE_EQ(empty_all.get_total_return(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_sharpe_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_sortino_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_information_ratio(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_maximum_drawdown(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_profit_factor(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_win_rate(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_beta(), 0.0);
  EXPECT_DOUBLE_EQ(empty_all.get_alpha(), 0.0);
}

TEST(MetricsTest, MismatchedBenchmarkLengthAndZeroEquityBoundary) {
  Metrics shorter_bench({100.0, 110.0, 120.0}, {}, {100.0}, {1.0});
  expect_all_finite(shorter_bench);
  EXPECT_DOUBLE_EQ(shorter_bench.get_beta(), 0.0);
  EXPECT_DOUBLE_EQ(shorter_bench.get_information_ratio(), 0.0);

  Metrics zero_start({0.0, 100.0, 50.0}, {}, {100.0, 105.0, 102.0}, {0.0});
  expect_all_finite(zero_start);
  EXPECT_DOUBLE_EQ(zero_start.get_total_return(), 0.0);
  EXPECT_DOUBLE_EQ(zero_start.get_annualized_return(), 0.0);
}

TEST(MetricsTest, EmptyRiskFreeCurveDefaultsToZeroRate) {
  Metrics m_empty({100.0, 110.0, 105.0, 120.0}, {}, {100.0, 102.0, 101.0, 104.0},
                  {});
  Metrics m_zero({100.0, 110.0, 105.0, 120.0}, {}, {100.0, 102.0, 101.0, 104.0},
                 {0.0, 0.0, 0.0, 0.0});

  EXPECT_DOUBLE_EQ(m_empty.get_sharpe_ratio(), m_zero.get_sharpe_ratio());
  EXPECT_DOUBLE_EQ(m_empty.get_sortino_ratio(), m_zero.get_sortino_ratio());
  EXPECT_DOUBLE_EQ(m_empty.get_alpha(), m_zero.get_alpha());
}
