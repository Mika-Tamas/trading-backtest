#pragma once

#include "fee_structure.h"

class Order_flat_fee : public FeeStructure {
private:
  double rate = 0.0;

public:
  Order_flat_fee(double rate);
  int quantity_from_cash(double cash, double price) const override;
  double calculate_fee(double price, int quantity) const override;
};