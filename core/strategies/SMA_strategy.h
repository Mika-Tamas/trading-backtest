#pragma once
#include "Strategy.h"
#include <vector>

class SMA_strategy : public Strategy {
private:
  std::int64_t warmup_over_timestamp;
  int slow_period;
  int fast_period;

  std::unordered_map<std::string, std::vector<double>>
      price_histories; // for SMA
  double calculate_SMA(const std::vector<double> &prices, int index_offset,
                       int period) const;
  int quantity_from_cash(const Portfolio &portfolio, const std::string &symbol,
                         double price) const;
  std::vector<Order> liquidate_ticker(const Portfolio &portfolio,
                                      const std::string &symbol,
                                      std::int64_t timestamp,
                                      double price) const;

public:
  SMA_strategy(std::int64_t start_timestamp, int slow, int fast);

  std::vector<Order> on_bar(const Bar &bar,
                            const Portfolio &portfolio) override;
  int get_warmup_days() const override;
};