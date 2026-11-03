#include "../include/order_flat_fee.h"

Order_flat_fee::Order_flat_fee(double rate) : rate(rate) {}

int Order_flat_fee::quantity_from_cash(double cash, double price) const {
  return (cash - rate) / price;
}

double Order_flat_fee::calculate_fee(double price, int quantity) const {
  return rate;
}