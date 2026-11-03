#include "../include/share_flat_fee.h"

Share_flat_fee::Share_flat_fee(double rate, double min_fee, double max_fee)
    : rate(rate), min_fee(min_fee), max_fee(max_fee) {}

int Share_flat_fee::quantity_from_cash(double cash, double price) const {
  int quantity_estimate = std::floor(cash / (price + rate));
  double fee_to_pay = calculate_fee(0, quantity_estimate);
  while (quantity_estimate * price + fee_to_pay > cash &&
         quantity_estimate >= 0) {
    quantity_estimate--;
    fee_to_pay = calculate_fee(0, quantity_estimate);
  }
  return quantity_estimate;
}

double Share_flat_fee::calculate_fee(double price, int quantity) const {
  double fee_to_pay = quantity * rate;
  if (min_fee > 0 && fee_to_pay < min_fee) {
    fee_to_pay = min_fee;
  } else if (max_fee > 0 && fee_to_pay > max_fee) {
    fee_to_pay = max_fee;
  }
  return fee_to_pay;
}