#pragma once
#include <cmath>
#include <vector>

class Metrics {
private:
  double MAR;
  std::vector<double>
  equity_to_percentage_returns(const std::vector<double> &equity_curve);

public:
  Metrics(double MAR);
  double get_sortino_ratio(const std::vector<double> &equity_curve);
};