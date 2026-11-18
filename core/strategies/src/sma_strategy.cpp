#include "../include/sma_strategy.h"
#include "../../engine/include/circular_buffer.hpp"
#include "../../engine/include/portfolio.h"
#include <cmath>

SMAStrategy::SMAStrategy(std::int64_t warmup_over_timestamp, int slow,
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

std::vector<Order> SMAStrategy::on_bar(const Bar &bar,
                                        const Portfolio &portfolio) {
  std::vector<Order> orders_to_execute;
  // multiple tickers support
  if (ticker_states.find(bar.ticker) == ticker_states.end()) {
    ticker_states[bar.ticker] =
        std::make_unique<TickerHistory>(slow_period, fast_period);
  }
  TickerHistory &ticker_history = *ticker_states[bar.ticker];
  ticker_history.consume_price(bar.close);

  if (bar.timestamp < warmup_over_timestamp) {
    return orders_to_execute;
  }

  if (ticker_history.fast_sma.get_size() < 2) {
    return orders_to_execute;
  }

  double fast_sma = ticker_history.get_cur_fast_sma();
  double prev_fast_sma = ticker_history.get_prev_fast_sma();
  double slow_sma = ticker_history.get_cur_slow_sma();
  double prev_slow_sma = ticker_history.get_prev_slow_sma();

  double price = bar.close;
  std::int64_t timestamp = bar.timestamp;
  std::string ticker = bar.ticker;

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

int SMAStrategy::get_warmup_days() const { return slow_period; }

void SMAStrategy::reset() { ticker_states.clear(); }

int SMAStrategy::get_unified_order_qty(const Portfolio &portfolio,
                                        std::string &ticker, double price,
                                        int direction) const {
  int current_qty = portfolio.get_position_quantity(ticker);
  double projected_cash = portfolio.get_cash() + (current_qty * price);
  int abs_target = portfolio.get_max_quantity(projected_cash, price);

  if (direction == 1 && current_qty < 0) {
    while (abs_target > 0 &&
           (abs_target - current_qty) * price +
                   portfolio.get_fee_for_order(price, abs_target - current_qty) >
               portfolio.get_cash() + 1e-9) {
      abs_target--;
    }
  }

  return (abs_target * direction) - current_qty;
}