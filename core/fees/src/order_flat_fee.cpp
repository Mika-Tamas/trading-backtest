#include "../include/order_flat_fee.h"
#include <cmath>

OrderFlatFee::OrderFlatFee(double rate) : rate(rate) {}

int OrderFlatFee::quantity_from_cash(double cash, double price) const {
  if (cash <= 0.0 || price <= 0.0 || rate < 0.0 || cash <= rate) {
    return 0;
  }
  return static_cast<int>(std::floor((cash - rate) / price));
}

double OrderFlatFee::calculate_fee(double price, int quantity) const {
  if (quantity <= 0 || price < 0.0 || rate <= 0.0) {
    return 0.0;
  }
  return rate;
}