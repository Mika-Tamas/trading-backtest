#include "../include/Backtester.h"
#include <unordered_map>

Backtester::Backtester(double initial_cash, std::shared_ptr<Strategy> strategy,
                       std::int64_t warmup_over_timestamp)
    : portfolio(initial_cash), strategy(strategy),
      warmup_over_timestamp(warmup_over_timestamp) {}

void Backtester::run(const std::vector<Bar> &bar_curve) {

  if (bar_curve.empty())
    return;

  // warmup data
  int index = 0;
  while (index < bar_curve.size() &&
         bar_curve[index].timestamp < warmup_over_timestamp) {
    strategy->on_bar(bar_curve[index], portfolio);
    index++;
  }

  if (index >= bar_curve.size())
    return;

  double initial_cash = portfolio.get_cash();
  double first_price = bar_curve[0].close;

  std::unordered_map<std::string, double> current_prices;

  equity_curve.push_back(initial_cash);
  timestamps.push_back(bar_curve[index].timestamp - 1);

  // run backtest
  for (; index < bar_curve.size(); index++) {
    Bar bar = bar_curve[index];

    current_prices[bar.symbol] = bar.close;
    auto orders = strategy->on_bar(
        bar, portfolio); // vector of liqvidation + entry || none
    for (Order order : orders) {
      portfolio.execute_order(order);
    }
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