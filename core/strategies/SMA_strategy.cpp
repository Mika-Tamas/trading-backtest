#include "SMA_strategy.h"
#include "Strategy.h"

SMA_strategy::SMA_strategy(int slow, int fast) {
  if (slow < fast) {
    slow_period = fast;
    fast_period = slow;
  } else {
    slow_period = slow;
    fast_period = fast;
  }
}

std::vector<Order> SMA_strategy::on_bar(const Bar &bar,
                                        const Portfolio &portfolio) {
  std::vector<Order> orders_to_execute;
  price_histories[bar.symbol].push_back(bar.close);

  const std::vector<double> &prices = price_histories[bar.symbol];

  if (prices.size() < slow_period + 1) {
    return orders_to_execute;
  }

  double fast_sma = calculate_SMA(prices, 0, fast_period);
  double prev_fast_sma = calculate_SMA(prices, 1, fast_period);
  double slow_sma = calculate_SMA(prices, 0, slow_period);
  double prev_slow_sma = calculate_SMA(prices, 1, slow_period);
  if (prev_fast_sma <= prev_slow_sma && fast_sma > slow_sma) {
    // buy
    Order order = {bar.symbol, bar.timestamp, 1, bar.close, 1};
    orders_to_execute.push_back(order);
  } else if (prev_fast_sma >= prev_slow_sma && fast_sma < slow_sma) {
    // sell
    Order order = {bar.symbol, bar.timestamp, 1, bar.close, -1};
    orders_to_execute.push_back(order);
  }

  return orders_to_execute;
}

double SMA_strategy::calculate_SMA(const std::vector<double> &prices,
                                   int index_offset, int period) const {
  if (prices.size() < period + index_offset) {
    return 0;
  }
  double price_total = 0;
  for (int i = prices.size() - period - index_offset;
       i < prices.size() - index_offset; ++i) {
    price_total += prices[i];
  }
  return price_total / period;
}