#pragma once
#include "Types.h"
#include <cstdint>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

#include "../../fees/FeeStructure.h "

class Portfolio {
private:
  double initial_cash;
  double cash;

  // ticker -> position
  std::unordered_map<std::string, Position> current_positions;
  std::vector<Trade> trade_history;

  std::shared_ptr<FeeStructure> fee_structure;

public:
  Portfolio(std::shared_ptr<FeeStructure> fee_structure, double initial_cash);
  void execute_order(const Order &order);
  double get_cash() const;
  double get_equity(
      const std::unordered_map<std::string, double> &current_prices) const;
  const std::vector<Trade> &get_trade_history() const;
  const std::unordered_map<std::string, Position> &get_positions() const;
  int get_max_quantity(double cash_available, double price) const;
  int get_position_quantity(const std::string &symbol) const;
};