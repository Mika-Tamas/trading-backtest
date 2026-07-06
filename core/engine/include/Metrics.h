#pragma once
#include "Types.h"
#include <cmath>
#include <vector>

class Metrics {
private:
  static constexpr double YEARLY_TRADING_DAYS = 252.0;
  std::vector<double>
  equity_to_percentage_returns(const std::vector<double> &equity_curve);
  double
  get_average_return(const std::vector<double> &daily_percentage_returns);
  double
  get_standard_deviation(const std::vector<double> &daily_percentage_returns,
                         double avg_return);
  double
  get_downside_deviation(const std::vector<double> &daily_percentage_returns,
                         double target_return);

public:
  Metrics();
  double get_annualized_return(const std::vector<double> &equity_curve);
  double get_sharpe_ratio(const std::vector<double> &equity_curve);
  double get_sortino_ratio(const std::vector<double> &equity_curve);
  double get_maximum_drawdown(const std::vector<double> &equity_curve);
  double get_calmar_ratio(const std::vector<double> &equity_curve);
  double get_profit_factor(const std::vector<Trade> &trade_history);
};