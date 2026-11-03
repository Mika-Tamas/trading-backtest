#include "../include/order_flat_fee.h"

OrderFlatFee::OrderFlatFee(double rate) : rate(rate) {}

int OrderFlatFee::quantity_from_cash(double cash, double price) const {
  return (cash - rate) / price;
}

double OrderFlatFee::calculate_fee(double price, int quantity) const {
  return rate;
}