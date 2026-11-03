#pragma once
#include "../../strategies/include/strategy.h"
#include "portfolio.h"
#include "types.h"
#include <cstdint>
#include <memory>
#include <unordered_map>
#include <vector>

class Backtester {
private:
  Portfolio portfolio;
  std::shared_ptr<Strategy> strategy;

  std::vector<double> equity_curve;
  std::vector<std::int64_t> timestamps;

  std::int64_t warmup_over_timestamp;

public:
  Backtester(double initial_cash, std::shared_ptr<Strategy> strategy,
             std::int64_t warmup_over_timestamp,
             std::shared_ptr<FeeStructure> fee_structure);
  void run(const std::vector<Bar> &historical_data);

  const Portfolio &get_portfolio() const;
  const std::vector<double> &get_equity_curve() const;
  const std::vector<std::int64_t> &get_timestamps() const;
};