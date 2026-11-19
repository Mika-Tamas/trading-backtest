#include "../include/share_flat_fee.h"
#include <algorithm>
#include <limits>

ShareFlatFee::ShareFlatFee(double rate, double min_fee, double max_fee)
    : rate(rate), min_fee(min_fee), max_fee(max_fee) {}

int ShareFlatFee::quantity_from_cash(double cash, double price) const {
  if (cash <= 0.0 || price <= 0.0 || rate < 0.0 ||
      (min_fee > 0.0 && cash <= min_fee)) {
    return 0;
  }

  double est = cash / (price + rate);
  double unclamped_fee = est * rate;

  if (min_fee > 0.0 && unclamped_fee < min_fee) {
    est = (cash - min_fee) / price;
  } else if (max_fee > 0.0 && unclamped_fee > max_fee) {
    est = (cash - max_fee) / price;
  }

  double floored = std::floor(est);
  double max_int = static_cast<double>(std::numeric_limits<int>::max());
  floored = std::clamp(floored, 0.0, max_int);
  int quantity_estimate = static_cast<int>(floored);

  double fee_to_pay = calculate_fee(price, quantity_estimate);
  while (quantity_estimate > 0 &&
         quantity_estimate * price + fee_to_pay > cash) {
    quantity_estimate--;
    fee_to_pay = calculate_fee(price, quantity_estimate);
  }

  return quantity_estimate;
}

double ShareFlatFee::calculate_fee(double price, int quantity) const {
  if (quantity <= 0 || price < 0.0 || rate < 0.0) {
    return 0.0;
  }
  double fee_to_pay = quantity * rate;
  if (min_fee > 0 && fee_to_pay < min_fee) {
    fee_to_pay = min_fee;
  } else if (max_fee > 0 && fee_to_pay > max_fee) {
    fee_to_pay = max_fee;
  }
  return fee_to_pay;
}