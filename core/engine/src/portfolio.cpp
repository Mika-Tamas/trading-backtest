#include "../include/portfolio.h"
#include <memory>

Portfolio::Portfolio(std::shared_ptr<FeeStructure> fee_structure,
                     double initial_cash)
    : initial_cash(initial_cash), cash(initial_cash),
      fee_structure(fee_structure) {}

void Portfolio::execute_order(const Order &order) {
  if (order.quantity <= 0 || order.price <= 0.0 ||
      (order.side != 1 && order.side != -1)) {
    return;
  }

  double total_cost = order.price * order.quantity;

  double current_order_fee =
      fee_structure ? fee_structure->calculate_fee(order.price, order.quantity)
                    : 0.0;

  auto it = current_positions.find(order.ticker);

  if (order.side > 0) {
    bool is_pure_short_cover =
        (it != current_positions.end() && it->second.quantity < 0 &&
         order.quantity <= std::abs(it->second.quantity));
    if (!is_pure_short_cover && cash + 1e-9 < total_cost + current_order_fee) {
      return;
    }
  }

  cash -= total_cost * order.side;
  cash -= current_order_fee;

  // Case 1: New position
  if (it == current_positions.end()) {
    Position p = {order.ticker, order.quantity * order.side, order.price,
                  order.timestamp, current_order_fee};
    current_positions[order.ticker] = p;
  } else {
    Position &p = it->second;

    bool is_reducing = (p.quantity > 0 && order.side < 0) ||
                       (p.quantity < 0 && order.side > 0);

    if (is_reducing) { // Case 2: Reducing
      // Total order = closed + remaining <- can reverse direction
      int closed_qty = std::min(std::abs(p.quantity), order.quantity);
      int position_side = (p.quantity > 0) ? 1 : -1;

      double pnl =
          (order.price - p.average_entry_price) * closed_qty * position_side;

      // Possible reverse -> fee split
      double entry_fee_portion =
          p.fee_paid * (static_cast<double>(closed_qty) / std::abs(p.quantity));
      double close_fee = current_order_fee *
                         (static_cast<double>(closed_qty) / order.quantity);

      Trade trade = {
          order.ticker,          p.entry_time, order.timestamp,
          p.average_entry_price, order.price,  closed_qty,
          position_side,         pnl,          entry_fee_portion + close_fee};
      trade_history.push_back(trade);

      // Check reverse (Long 10 -> Short 5)
      int remaining_order_qty = order.quantity - closed_qty;
      if (remaining_order_qty > 0) {
        p.quantity = remaining_order_qty * order.side;
        p.average_entry_price = order.price;
        p.entry_time = order.timestamp;
        p.fee_paid = current_order_fee - close_fee;
      } else {
        p.quantity += order.quantity * order.side;
        p.fee_paid -= entry_fee_portion;
        if (p.quantity == 0) {
          current_positions.erase(it);
        }
      }
    } else { // Case 3: Scaling up
      double after_value =
          (p.quantity * p.average_entry_price) + total_cost * order.side;
      p.quantity += order.quantity * order.side;
      p.average_entry_price = after_value / p.quantity;
      p.fee_paid += current_order_fee;
    }
  }
}

double Portfolio::get_cash() const { return cash; }

double Portfolio::get_equity(
    const std::unordered_map<std::string, double> &current_prices) const {
  double total_equity = cash;
  for (const auto &[ticker, position] : current_positions) {
    auto price_it = current_prices.find(ticker);
    if (price_it == current_prices.end()) {
      total_equity += position.average_entry_price * position.quantity;
    } else {
      total_equity += price_it->second * position.quantity;
    }
  }

  return total_equity;
}

const std::vector<Trade> &Portfolio::get_trade_history() const {
  return trade_history;
}
const std::unordered_map<std::string, Position> &
Portfolio::get_positions() const {
  return current_positions;
}

int Portfolio::get_max_quantity(double cash_available, double price) const {
  return fee_structure->quantity_from_cash(cash_available, price);
}

int Portfolio::get_position_quantity(const std::string &ticker) const {
  auto it = current_positions.find(ticker);
  if (it != current_positions.end()) {
    return it->second.quantity;
  } else {
    return 0;
  }
}

double Portfolio::get_fee_for_order(double price, int quantity) const {
  return fee_structure ? fee_structure->calculate_fee(price, quantity) : 0.0;
}