#include "../include/Backtester.h"
#include <unordered_map>

Backtester::Backtester(double initial_cash, std::shared_ptr<Strategy> strategy)
    : portfolio(initial_cash), strategy(strategy) {}

void Backtester::run(const std::vector<Bar> &historical_data) {

  if (historical_data.empty())
    return;

  double initial_cash = portfolio.get_cash();
  double first_price = historical_data[0].close;

  std::unordered_map<std::string, double> current_prices;

  // starting values
  benchmark_curve.push_back(initial_cash);
  equity_curve.push_back(initial_cash);
  timestamps.push_back(historical_data[0].timestamp - 1);

  for (auto bar : historical_data) {
    current_prices[bar.symbol] = bar.close;
    auto orders = strategy->on_bar(
        bar, portfolio); // vector of liqvidation + entry || none
    for (Order order : orders) {
      portfolio.execute_order(order);
    }
    benchmark_curve.push_back(initial_cash * (bar.close / first_price));
    equity_curve.push_back(portfolio.get_equity(current_prices));
    timestamps.push_back(bar.timestamp);
  }

  // Liquidate when over
  for (auto position : portfolio.get_positions()) {
    int side_to_close = (position.second.quantity > 0) ? -1 : 1;
    portfolio.execute_order({position.first, timestamps.back(),
                             std::abs(position.second.quantity),
                             current_prices[position.first], side_to_close});
  }
  benchmark_curve.push_back(benchmark_curve.back());
  equity_curve.push_back(portfolio.get_equity(current_prices));
  timestamps.push_back(timestamps.back() + 1);
}

const Portfolio &Backtester::get_portfolio() const { return portfolio; }
const std::vector<double> &Backtester::get_equity_curve() const {
  return equity_curve;
}
const std::vector<std::int64_t> &Backtester::get_timestamps() const {
  return timestamps;
}
const std::vector<double> &Backtester::get_benchmark_curve() const {
  return benchmark_curve;
}