#include "SMA_strategy.h"
#include <cmath>

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

  double price = bar.close;
  std::int64_t timestamp = bar.timestamp;
  std::string ticker = bar.symbol;

  if (prev_fast_sma <= prev_slow_sma && fast_sma > slow_sma) {
    // liqvidate
    std::vector<Order> close_orders =
        liquidate_ticker(portfolio, ticker, timestamp, price);
    orders_to_execute.insert(orders_to_execute.end(), close_orders.begin(),
                             close_orders.end());
    // buy
    Order order = {ticker, timestamp,
                   quantity_from_cash(portfolio, ticker, price), price, 1};
    orders_to_execute.push_back(order);
  } else if (prev_fast_sma >= prev_slow_sma && fast_sma < slow_sma) {
    // liqvidate
    std::vector<Order> close_orders =
        liquidate_ticker(portfolio, ticker, timestamp, price);
    orders_to_execute.insert(orders_to_execute.end(), close_orders.begin(),
                             close_orders.end());
    // sell
    Order order = {ticker, timestamp,
                   quantity_from_cash(portfolio, ticker, price), price, -1};
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

std::vector<Order> SMA_strategy::liquidate_ticker(const Portfolio &portfolio,
                                                  const std::string &symbol,
                                                  std::int64_t timestamp,
                                                  double price) const {

  std::vector<Order> close_orders;
  const auto &positions = portfolio.get_positions();

  auto it = positions.find(symbol);
  if (it != positions.end() && it->second.quantity != 0) {
    int side_to_close = (it->second.quantity > 0) ? -1 : 1;
    close_orders.push_back({symbol, timestamp, std::abs(it->second.quantity),
                            price, side_to_close});
  }
  return close_orders;
}

int SMA_strategy::quantity_from_cash(const Portfolio &portfolio,
                                     const std::string &symbol,
                                     double price) const {
  double projected_cash = portfolio.get_cash();
  const auto &positions = portfolio.get_positions();

  auto it = positions.find(symbol);
  if (it != positions.end()) {
    projected_cash += it->second.quantity * price;
  }

  return std::floor(projected_cash / price);
}
