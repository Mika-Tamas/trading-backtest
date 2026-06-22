#pragma once
#include "Types.h"
#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

class Portfolio {
private:
  double initial_cash;
  double cash;

  // ticker -> position
  std::unordered_map<std::string, Position> current_positions;
  std::vector<Trade> trade_history;

public:
  Portfolio(double initial_cash);
  void execute_order(const Order &order);
  double get_cash() const;
  double get_equity(
      const std::unordered_map<std::string, double> &current_prices) const;
};