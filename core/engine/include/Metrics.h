#pragma once
#include "Types.h"
#include <cmath>
#include <vector>

class Metrics {
private:
  static constexpr double YEARLY_TRADING_DAYS = 252.0;

  std::vector<double> equity_curve;
  std::vector<double> daily_percentage_returns;
  std::vector<Trade> trade_history;
  std::vector<double> benchmark_curve;
  std::vector<double> benchmark_daily_percentage_returns;
  std::vector<double> risk_free_rate_curve;
  double average_daily_risk_free_return;
  double average_daily_strategy_return;
  double average_daily_benchmark_return;
  double maximum_drawdown;

  std::vector<double>
  equity_to_percentage_returns(const std::vector<double> &equity_curve);
  double get_average_daily_risk_free_return();
  double
  get_average_daily_return(const std::vector<double> &daily_percentage_returns);
  double
  get_standard_deviation(const std::vector<double> &daily_percentage_returns,
                         double avg_return);
  double
  get_downside_deviation(const std::vector<double> &daily_percentage_returns,
                         double target_return);

  double calculate_maximum_drawdown();

public:
  Metrics(std::vector<double> equity_curve, std::vector<Trade> trade_history,
          std::vector<double> benchmark_curve,
          std::vector<double> risk_free_rate_curve);
  double get_total_return();
  double get_annualized_return();
  double get_sharpe_ratio();
  double get_sortino_ratio();
  double get_maximum_drawdown();
  double get_calmar_ratio();
  double get_profit_factor();
  double get_win_rate();
};