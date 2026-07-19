#include "SMA_strategy.h"
#include "CircularBuffer.hpp"
#include "Portfolio.h"
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
    int order_qty = get_unified_order_qty(portfolio, ticker, price, 1);
    // buy
    if (order_qty > 0) {
      Order order = {ticker, timestamp, order_qty, price, 1};
      orders_to_execute.push_back(order);
    }
  } else if (prev_fast_sma >= prev_slow_sma && fast_sma < slow_sma) {
    int order_qty = get_unified_order_qty(portfolio, ticker, price, -1);
    // sell
    if (order_qty < 0) {
      Order order = {ticker, timestamp, std::abs(order_qty), price, -1};
      orders_to_execute.push_back(order);
    }
  }

  return orders_to_execute;
}

int SMA_strategy::get_warmup_days() const { return slow_period; }

int SMA_strategy::get_unified_order_qty(const Portfolio &portfolio,
                                        std::string &ticker, double price,
                                        int direction) const {
  int current_qty = portfolio.get_position_quantity(ticker);
  double projected_cash = portfolio.get_cash() + (current_qty * price);
  int target_qty =
      portfolio.get_max_quantity(projected_cash, price) * direction;
  int order_qty = target_qty - current_qty;
  return order_qty;
}