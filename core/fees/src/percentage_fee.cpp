#include "../include/percentage_fee.h"

PercentageFee::PercentageFee(double rate, double min_fee, double max_fee)
    : rate(rate), min_fee(min_fee), max_fee(max_fee) {}

int PercentageFee::quantity_from_cash(double cash, double price) const {
  int quantity_estimate = std::floor(cash / (price * (1.0 + rate)));
  double fee_to_pay = calculate_fee(price, quantity_estimate);

  while (quantity_estimate * price + fee_to_pay > cash &&
         quantity_estimate > 0) {
    quantity_estimate--;
    fee_to_pay = calculate_fee(price, quantity_estimate);
  }

  return quantity_estimate;
}

double PercentageFee::calculate_fee(double price, int quantity) const {
  double fee_to_pay = price * quantity * rate;
  if (min_fee > 0 && fee_to_pay < min_fee) {
    fee_to_pay = min_fee;
  } else if (max_fee > 0 && fee_to_pay > max_fee) {
    fee_to_pay = max_fee;
  }
  return fee_to_pay;
}