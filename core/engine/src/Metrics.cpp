#include "../include/Metrics.h"
#include "../include/Types.h"
#include <algorithm>
#include <cmath>
#include <vector>

Metrics::Metrics() {} // TODO: risk free rate vector

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

double Metrics::get_average_return(
    const std::vector<double> &daily_percentage_returns) {
  if (daily_percentage_returns.empty())
    return 0.0;
  double sum_return = 0.0;
  for (double ret : daily_percentage_returns) {
    sum_return += ret;
  }
  double avg_return = sum_return / daily_percentage_returns.size();
  return avg_return;
}
double Metrics::get_standard_deviation(
    const std::vector<double> &daily_percentage_returns, double avg_return) {
  double sum_squared_deviation = 0.0;
  for (double ret : daily_percentage_returns) {
    double deviation = std::min(0.0, ret - avg_return);
    sum_squared_deviation += (deviation * deviation);
  }
  double standard_variance =
      sum_squared_deviation / daily_percentage_returns.size();

  if (standard_variance == 0.0)
    return 0.0;

  double standard_dev = std::sqrt(standard_variance);
  return standard_dev;
}
double Metrics::get_downside_deviation(
    const std::vector<double> &daily_percentage_returns, double target_return) {
  double sum_squared_downside = 0.0;
  for (double ret : daily_percentage_returns) {
    double downside = std::min(0.0, ret - target_return);
    sum_squared_downside += (downside * downside);
  }
  double downside_variance =
      sum_squared_downside / daily_percentage_returns.size();

  if (downside_variance == 0.0)
    return 0.0;

  double downside_dev = std::sqrt(downside_variance);
  return downside_dev;
}
double Metrics::get_annualized_return(const std::vector<double> &equity_curve) {
  // CAGR
  if (equity_curve.size() < 2)
    return 0.0;
  if (equity_curve.front() == 0.0)
    return 0.0;
  double total_return = equity_curve.back() / equity_curve.front();
  double time_factor = 1.0 / (equity_curve.size() / YEARLY_TRADING_DAYS);

  double cagr = std::pow(total_return, time_factor) - 1.0;

  return cagr;
}
double Metrics::get_sharpe_ratio(const std::vector<double> &equity_curve) {
  auto daily_percentage_returns = equity_to_percentage_returns(equity_curve);
  if (daily_percentage_returns.empty())
    return 0.0;
  double avg_return = get_average_return(daily_percentage_returns);
  double standard_dev =
      get_standard_deviation(daily_percentage_returns, avg_return);
  if (standard_dev == 0.0)
    return 0.0;
  double daily_sharpe = (avg_return - 0.001) / standard_dev; //

  double annualized_sharpe = daily_sharpe * std::sqrt(YEARLY_TRADING_DAYS);
  return annualized_sharpe;
}
double Metrics::get_sortino_ratio(const std::vector<double> &equity_curve) {
  // (Average return - target return) / Downside Deviation
  double target_return = 0.001; //
  auto daily_percentage_returns = equity_to_percentage_returns(equity_curve);
  if (daily_percentage_returns.empty())
    return 0.0;
  double avg_return = get_average_return(daily_percentage_returns);
  double downside_dev =
      get_downside_deviation(daily_percentage_returns, target_return);
  if (downside_dev == 0.0)
    return 0.0;
  double daily_sortino = (avg_return - target_return) / downside_dev;

  double annualized_sortino = daily_sortino * std::sqrt(YEARLY_TRADING_DAYS);
  return annualized_sortino;
}

double Metrics::get_maximum_drawdown(const std::vector<double> &equity_curve) {
  if (equity_curve.size() < 2)
    return 0.0;

  double peak = equity_curve[0];
  double max_dd = 0.0;

  for (int i = 1; i < equity_curve.size(); ++i) {
    double drop = (peak - equity_curve[i]) / peak;
    if (equity_curve[i] > peak) {
      peak = equity_curve[i];
    } else if (drop > max_dd) {
      max_dd = drop;
    }
  }

  return max_dd;
}

double Metrics::get_calmar_ratio(const std::vector<double> &equity_curve) {
  double annualized_return = get_annualized_return(equity_curve);
  double max_dd = get_maximum_drawdown(equity_curve);

  if (max_dd == 0.0) {
    if (annualized_return > 0.0) {
      return 999.0; // perfect strategy (INFINITY)
    } else {
      return 0.0; // no trades executed
    }
  }
  double calmar_ratio = annualized_return / max_dd;
  return calmar_ratio;
}

double Metrics::get_profit_factor(const std::vector<Trade> &trade_history) {
  double gross_profit = 0.0;
  double gross_loss = 0.0;

  for (const Trade &trade : trade_history) {
    if (trade.realized_pnl > 0) {
      gross_profit += trade.realized_pnl;
    } else {
      gross_loss -= trade.realized_pnl; // positive loss
    }
  }
  if (gross_loss == 0.0) {
    return gross_profit > 0.0 ? 999.0 : 0.0; // (INFINITY)
  }
  return gross_profit / gross_loss;
}