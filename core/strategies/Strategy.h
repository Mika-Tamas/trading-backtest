#pragma once
#include "../engine/include/Portfolio.h"
#include "../engine/include/Types.h"
#include <vector>

class Strategy {
public:
  virtual ~Strategy() = default;
  virtual std::vector<Order> on_bar(const Bar &bar,
                                    const Portfolio &portfolio) = 0;
};