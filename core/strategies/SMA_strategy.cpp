#include "SMA_strategy.h"
#include "CircularBuffer.hpp"
#include <cmath>

SMA_strategy::SMA_strategy(std::int64_t warmup_over_timestamp, int slow,
                           int fast)
    : warmup_over_timestamp(warmup_over_timestamp) {
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
  // multiple tickers support
  if (ticker_states.find(bar.symbol) == ticker_states.end()) {
    ticker_states[bar.symbol] =
        std::make_unique<TickerHistory>(slow_period, fast_period);
  }
  TickerHistory &ticker_history = *ticker_states[bar.symbol];
  ticker_history.consume_price(bar.close);

  if (bar.timestamp < warmup_over_timestamp) {
    return orders_to_execute;
  }

  if (ticker_history.fast_sma.get_size() < 2) {
    return orders_to_execute;
  }

  double fast_sma = ticker_history.get_cur_fast_SMA();
  double prev_fast_sma = ticker_history.get_prev_fast_SMA();
  double slow_sma = ticker_history.get_cur_slow_SMA();
  double prev_slow_sma = ticker_history.get_prev_slow_SMA();

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

int SMA_strategy::get_warmup_days() const { return slow_period; }