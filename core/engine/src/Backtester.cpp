#include "../include/Backtester.h"
#include <algorithm>
#include <unordered_map>

Backtester::Backtester(double initial_cash, std::shared_ptr<Strategy> strategy)
    : portfolio(initial_cash), strategy(strategy) {}

void Backtester::run(const std::vector<Bar> &historical_data) {

  if (historical_data.empty())
    return;

  std::unordered_map<std::string, double> current_prices;

  // starting values
  equity_curve.push_back(portfolio.get_equity(current_prices));
  timestamps.push_back(historical_data[0].timestamp - 1); // -1 hardcoded

  for (auto bar : historical_data) {
    current_prices[bar.symbol] = bar.close;
    auto orders =
        strategy->on_bar(bar, portfolio); // vector | currently 1 or 0 elems
    for (Order order : orders) {
      portfolio.execute_order(order);
    }

    equity_curve.push_back(portfolio.get_equity(current_prices));
    timestamps.push_back(bar.timestamp);
  }
}

const Portfolio &Backtester::get_portfolio() const { return portfolio; }
const std::vector<double> &Backtester::get_equity_curve() const {
  return equity_curve;
}
const std::vector<std::int64_t> &Backtester::get_timestamps() const {
  return timestamps;
}