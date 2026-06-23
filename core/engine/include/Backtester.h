#pragma once
#include "../../strategies/Strategy.h"
#include "Portfolio.h"
#include "Types.h"
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

public:
  Backtester(double initial_cash, std::shared_ptr<Strategy> strategy);
  void run(const std::vector<Bar> &historical_data);

  const Portfolio &get_portfolio() const;
  const std::vector<double> &get_equity_curve() const;
  const std::vector<std::int64_t> &get_timestamps() const;
};