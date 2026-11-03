#pragma once
#include "../../engine/include/portfolio.h"
#include "../../engine/include/types.h"
#include <vector>

class Strategy {
private:
  std::int64_t warmup_over_timestamp;

public:
  virtual ~Strategy() = default;
  virtual std::vector<Order> on_bar(const Bar &bar,
                                    const Portfolio &portfolio) = 0;
  virtual int get_warmup_days() const = 0;
};