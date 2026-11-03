#include "../include/metrics.h"
#include "../include/types.h"
#include <algorithm>
#include <cmath>
#include <vector>

Metrics::Metrics(std::vector<double> equity_curve,
                 std::vector<Trade> trade_history,
                 std::vector<double> benchmark_curve,
                 std::vector<double> risk_free_rate_curve)
    : equity_curve(std::move(equity_curve)),
      trade_history(std::move(trade_history)),
      benchmark_curve(std::move(benchmark_curve)),
      risk_free_rate_curve(std::move(risk_free_rate_curve)) {

  daily_percentage_returns = equity_to_percentage_returns(this->equity_curve);
  benchmark_daily_percentage_returns =
      equity_to_percentage_returns(this->benchmark_curve);

  average_daily_risk_free_return = get_average_daily_risk_free_return();
  average_daily_strategy_return =
      get_average_daily_return(daily_percentage_returns);
  average_daily_benchmark_return =
      get_average_daily_return(benchmark_daily_percentage_returns);

  maximum_drawdown = calculate_maximum_drawdown();
  beta = calculate_beta();
}
//-------------------------PRIVATE-----------------------------
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

double Metrics::get_average_daily_risk_free_return() {
  double avg_rf = 0.001;
  if (!risk_free_rate_curve.empty()) {
    double sum = 0.0;
    for (double r : risk_free_rate_curve)
      sum += r;
    avg_rf = (sum / risk_free_rate_curve.size()) / 100.0 / YEARLY_TRADING_DAYS;
  }
  return avg_rf;
}

double Metrics::get_average_daily_return(
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
    double deviation = ret - avg_return;
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

double Metrics::calculate_maximum_drawdown() {
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

  return max_dd * 100;
}

double Metrics::calculate_beta() {
  double cov_sum = 0.0;
  double var_sum = 0.0;

  for (size_t i = 0; i < daily_percentage_returns.size(); ++i) {
    double diff_strat =
        daily_percentage_returns[i] - average_daily_strategy_return;
    double diff_bench =
        benchmark_daily_percentage_returns[i] - average_daily_benchmark_return;

    cov_sum += diff_strat * diff_bench;
    var_sum += diff_bench * diff_bench;
  }

  if (var_sum == 0.0)
    return 0.0;
  // Size division cancels out
  double beta = cov_sum / var_sum;
  return beta;
}

//-------------------------PUBLIC-----------------------------
double Metrics::get_total_return() {
  if (equity_curve.empty())
    return 0.0;
  double total_return =
      (equity_curve.back() - equity_curve.front()) / equity_curve.front() * 100;
  return total_return;
}

double Metrics::get_annualized_return() {
  // CAGR
  if (equity_curve.size() < 2)
    return 0.0;
  if (equity_curve.front() == 0.0)
    return 0.0;
  double total_return = equity_curve.back() / equity_curve.front();
  double time_factor = 1.0 / (equity_curve.size() / YEARLY_TRADING_DAYS);

  double cagr = std::pow(total_return, time_factor) - 1.0;

  return cagr * 100;
}
double Metrics::get_sharpe_ratio() {
  if (daily_percentage_returns.empty())
    return 0.0;
  double avg_return = average_daily_strategy_return;
  double standard_dev =
      get_standard_deviation(daily_percentage_returns, avg_return);
  if (standard_dev == 0.0)
    return 0.0;

  double avg_rf = average_daily_risk_free_return;

  double daily_sharpe = (avg_return - avg_rf) / standard_dev;

  double annualized_sharpe = daily_sharpe * std::sqrt(YEARLY_TRADING_DAYS);
  return annualized_sharpe;
}
double Metrics::get_sortino_ratio() {
  // (Average return - target return) / Downside Deviation
  double target_return = average_daily_risk_free_return;
  if (daily_percentage_returns.empty())
    return 0.0;
  double avg_return = average_daily_strategy_return;
  double downside_dev =
      get_downside_deviation(daily_percentage_returns, target_return);
  if (downside_dev == 0.0)
    return 0.0;
  double daily_sortino = (avg_return - target_return) / downside_dev;

  double annualized_sortino = daily_sortino * std::sqrt(YEARLY_TRADING_DAYS);
  return annualized_sortino;
}

double Metrics::get_information_ratio() {
  std::vector<double> diff(daily_percentage_returns.size());

  for (int i = 0; i < daily_percentage_returns.size(); ++i) {
    diff[i] =
        daily_percentage_returns[i] - benchmark_daily_percentage_returns[i];
  }
  double mean = average_daily_strategy_return - average_daily_benchmark_return;
  double daily_tracking_error = get_standard_deviation(diff, mean);
  double daily_IR = mean / daily_tracking_error;
  double annualized_IR = daily_IR * std::sqrt(YEARLY_TRADING_DAYS);

  return annualized_IR;
}

double Metrics::get_maximum_drawdown() { return maximum_drawdown; }

double Metrics::get_calmar_ratio() {
  double annualized_return = get_annualized_return();
  double max_dd = maximum_drawdown;

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

double Metrics::get_profit_factor() {
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

double Metrics::get_win_rate() {
  if (trade_history.empty())
    return 0.0;
  int wins = 0;
  for (const Trade &trade : trade_history) {
    if (trade.realized_pnl > 0.0) {
      wins++;
    }
  }
  double win_rate = static_cast<double>(wins) / trade_history.size();
  return win_rate * 100;
}

double Metrics::get_beta() { return beta; }

double Metrics::get_alpha() {
  double annualized_strategy_return =
      average_daily_strategy_return * YEARLY_TRADING_DAYS;
  double annualized_risk_free_return =
      average_daily_risk_free_return * YEARLY_TRADING_DAYS;
  double annualized_benchmark_return =
      average_daily_benchmark_return * YEARLY_TRADING_DAYS;

  double alpha =
      annualized_strategy_return -
      (annualized_risk_free_return +
       beta * (annualized_benchmark_return - annualized_risk_free_return));
  return alpha * 100;
}