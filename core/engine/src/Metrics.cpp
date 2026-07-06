#include "../include/Metrics.h"
#include <algorithm>
#include <cmath>
#include <vector>

Metrics::Metrics(double MAR) : MAR(0.0) {} // TODO: risk free rate vector

std::vector<double>
Metrics::equity_to_percentage_returns(const std::vector<double> &equity_curve) {
  std::vector<double> daily_returns;
  if (equity_curve.size() < 2)
    return daily_returns;

  daily_returns.reserve(equity_curve.size() - 1);

  for (int i = 1; i < equity_curve.size(); ++i) {
    double prev = equity_curve[i - 1];
    double curr = equity_curve[i];
    if (prev != 0.0) {
      daily_returns.push_back((curr - prev) / prev);
    } else {
      daily_returns.push_back(0.0);
    }
  }

  return daily_returns;
}

double Metrics::get_sortino_ratio(const std::vector<double> &equity_curve) {
  // (Average return - MAR) / Downside Deviation
  auto daily_percentage_returns = equity_to_percentage_returns(equity_curve);
  if (daily_percentage_returns.empty())
    return 0.0;

  double sum_return = 0.0;
  double sum_squared_downside = 0.0;
  for (double ret : daily_percentage_returns) {
    sum_return += ret;
    double downside = std::min(0.0, ret - MAR);
    sum_squared_downside += (downside * downside);
  }
  double avg_return = sum_return / daily_percentage_returns.size();
  double downside_variance =
      sum_squared_downside / daily_percentage_returns.size();

  if (downside_variance == 0.0)
    return 0.0;

  double downside_dev = std::sqrt(downside_variance);
  double daily_sortino = (avg_return - MAR) / downside_dev;

  double annualized_sortino =
      daily_sortino * std::sqrt(252.0); // trading days in a year
  return annualized_sortino;
}