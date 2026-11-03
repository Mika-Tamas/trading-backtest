#pragma once

#include "fee_structure.h"

class PercentageFee : public FeeStructure {
private:
  double rate = 0.0;
  double min_fee = -1.0;
  double max_fee = -1.0;

public:
  PercentageFee(double rate, double min_fee, double max_fee);
  int quantity_from_cash(double cash, double price) const override;
  double calculate_fee(double price, int quantity) const override;
};