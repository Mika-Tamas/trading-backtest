#pragma once
#include "../engine/include/Portfolio.h"
#include "../engine/include/Types.h"
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