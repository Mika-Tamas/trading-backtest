#include "../include/Portfolio.h"

Portfolio::Portfolio(double initial_cash)
    : initial_cash(initial_cash), cash(initial_cash) {}

void Portfolio::execute_order(const Order &order) {
  double total_cost = order.price * order.quantity;

  cash -= total_cost * order.side;

  auto it = current_positions.find(
      order.symbol); // std::unordered_map<std::string, Position>::iterator it

  // Case 1: New position
  if (it == current_positions.end()) {
    Position p = {order.symbol, order.quantity, order.price, order.timestamp};
    current_positions[order.symbol] = p;
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

      Trade trade = {order.symbol,          p.entry_time, order.timestamp,
                     p.average_entry_price, order.price,  closed_qty,
                     position_side,         pnl};
      trade_history.push_back(trade);

      // Check reverse (Long 10 -> Short 5)
      int remaining_order_qty = order.quantity - closed_qty;
      if (remaining_order_qty > 0) {
        p.quantity = remaining_order_qty * order.side;
        p.average_entry_price = order.price;
        p.entry_time = order.timestamp;
      } else {
        p.quantity += order.quantity * order.side;
        if (p.quantity == 0) {
          current_positions.erase(it);
        }
      }
    } else { // Case 3: Scaling up
      double after_value =
          (p.quantity * p.average_entry_price) + total_cost * order.side;
      p.quantity += order.quantity * order.side;
      p.average_entry_price = after_value / p.quantity;
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