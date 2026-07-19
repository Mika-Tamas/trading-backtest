#pragma once
#include "../include/CircularBuffer.hpp"
#include "Strategy.h"
#include <memory>
#include <unordered_map>
#include <vector>

class SMA_strategy : public Strategy {
private:
  std::int64_t warmup_over_timestamp;
  int slow_period;
  int fast_period;

  struct TickerHistory {
    CircularBuffer<double> prices;
    CircularBuffer<double> fast_sma;
    CircularBuffer<double> slow_sma;

    const int fast_period;
    const int slow_period;

    double fast_sum = 0.0;
    double fast_comp = 0.0;
    double slow_sum = 0.0;
    double slow_comp = 0.0;

    TickerHistory(int slow_p, int fast_p)
        : prices(slow_p), fast_sma(2), slow_sma(2), fast_period(fast_p),
          slow_period(slow_p) {}

    void consume_price(double price) {
      double fast_to_remove =
          prices.get_size() >= fast_period
              ? prices.get_prev(fast_period - 1) // -1 -> new not yet pushed
              : 0.0;
      double slow_to_remove =
          prices.get_size() >= slow_period ? prices.get_oldest() : 0.0;

      apply_kahan(fast_sum, fast_comp, price, fast_to_remove);
      apply_kahan(slow_sum, slow_comp, price, slow_to_remove);

      prices.push(price);

      if (prices.get_size() >= slow_period) {
        fast_sma.push(fast_sum / fast_period);
        slow_sma.push(slow_sum / slow_period);
      }
    }
    double get_prev_fast_SMA() { return fast_sma.get_oldest(); }
    double get_prev_slow_SMA() { return slow_sma.get_oldest(); }
    double get_cur_fast_SMA() { return fast_sma.get_newest(); }
    double get_cur_slow_SMA() { return slow_sma.get_newest(); }

  private:
    void apply_kahan(double &sum, double &comp, double to_add,
                     double to_remove) {
      double y_sub = -to_remove - comp;
      double t_sub = sum + y_sub;
      comp = (t_sub - sum) - y_sub;
      sum = t_sub;

      double y_add = to_add - comp;
      double t_add = sum + y_add;
      comp = (t_add - sum) - y_add;
      sum = t_add;
    }
  };

  std::unordered_map<std::string, std::unique_ptr<TickerHistory>> ticker_states;

public:
  SMA_strategy(std::int64_t start_timestamp, int slow, int fast);

  std::vector<Order> on_bar(const Bar &bar,
                            const Portfolio &portfolio) override;
  int get_warmup_days() const override;
  int get_unified_order_qty(const Portfolio &portfolio, std::string &ticker,
                            double price, int direction) const;
};