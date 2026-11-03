#pragma once

#include "../../engine/include/types.h"
#include <cmath>

class FeeStructure {
public:
  virtual ~FeeStructure() = default;
  virtual int quantity_from_cash(double cash, double price) const = 0;
  virtual double calculate_fee(double price, int quantity) const = 0;
};