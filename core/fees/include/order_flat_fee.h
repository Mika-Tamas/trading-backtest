#pragma once

#include "fee_structure.h"

class OrderFlatFee : public FeeStructure {
private:
  double rate = 0.0;

public:
  OrderFlatFee(double rate);
  int quantity_from_cash(double cash, double price) const override;
  double calculate_fee(double price, int quantity) const override;
};