#pragma once
#include <cstdint>
#include <iostream>
#include <string>

struct Bar {
  std::string ticker;
  std::int64_t timestamp;
  double open;
  double high;
  double low;
  double close;
  double volume;
};

struct Order {
  std::string ticker;
  std::int64_t timestamp;
  int quantity;
  double price;
  int side;
};

struct Trade {
  std::string ticker;
  std::int64_t entry_time;
  std::int64_t exit_time;
  double entry_price;
  double exit_price;
  int quantity;
  int side;
  double realized_pnl;
  double fee_paid;
};

struct Position {
  std::string ticker;
  int quantity;
  double average_entry_price;
  std::int64_t entry_time;
  double fee_paid;
};