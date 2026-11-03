#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "../../fees/include/fee_structure.h"
#include "../../fees/include/order_flat_fee.h"
#include "../../fees/include/percentage_fee.h"
#include "../../fees/include/share_flat_fee.h"
#include "../../strategies/include/sma_strategy.h"
#include "../../strategies/include/strategy.h"
#include "../include/backtester.h"
#include "../include/metrics.h"
#include "../include/portfolio.h"
#include "../include/types.h"

namespace py = pybind11;

PYBIND11_MODULE(backtest_core, m) {
  m.doc() = "C++ Backtest simulation engine";

  // structs
  py::class_<Trade>(m, "Trade")
      .def_readwrite("symbol", &Trade::symbol)
      .def_readwrite("entry_time", &Trade::entry_time)
      .def_readwrite("exit_time", &Trade::exit_time)
      .def_readwrite("entry_price", &Trade::entry_price)
      .def_readwrite("exit_price", &Trade::exit_price)
      .def_readwrite("quantity", &Trade::quantity)
      .def_readwrite("side", &Trade::side)
      .def_readwrite("realized_pnl", &Trade::realized_pnl)
      .def_readwrite("fee_paid", &Trade::fee_paid);
  py::class_<Position>(m, "Position")
      .def_readwrite("symbol", &Position::symbol)
      .def_readwrite("quantity", &Position::quantity)
      .def_readwrite("average_entry_price", &Position::average_entry_price)
      .def_readwrite("entry_time", &Position::entry_time)
      .def_readwrite("fee_paid", &Position::fee_paid);
  py::class_<Bar>(m, "Bar")
      .def(py::init<std::string, std::int64_t, double, double, double, double,
                    double>())
      .def_readwrite("symbol", &Bar::symbol)
      .def_readwrite("timestamp", &Bar::timestamp)
      .def_readwrite("open", &Bar::open)
      .def_readwrite("high", &Bar::high)
      .def_readwrite("low", &Bar::low)
      .def_readwrite("close", &Bar::close)
      .def_readwrite("volume", &Bar::volume);

  // methods
  py::class_<Backtester>(m, "Backtester")
      .def(py::init<double, std::shared_ptr<Strategy>, std::int64_t,
                    std::shared_ptr<FeeStructure>>())
      .def("run", &Backtester::run)
      .def("get_portfolio", &Backtester::get_portfolio)
      .def("get_equity_curve", &Backtester::get_equity_curve)
      .def("get_timestamps", &Backtester::get_timestamps);
  py::class_<Portfolio>(m, "Portfolio")
      .def("get_cash", &Portfolio::get_cash)
      .def("get_equity", &Portfolio::get_equity)
      .def("get_trade_history", &Portfolio::get_trade_history)
      .def("get_positions", &Portfolio::get_positions);

  py::class_<Metrics>(m, "Metrics")
      .def(py::init<std::vector<double>, std::vector<Trade>,
                    std::vector<double>, std::vector<double>>())
      .def("get_total_return", &Metrics::get_total_return)
      .def("get_annualized_return", &Metrics::get_annualized_return)
      .def("get_sharpe_ratio", &Metrics::get_sharpe_ratio)
      .def("get_sortino_ratio", &Metrics::get_sortino_ratio)
      .def("get_information_ratio", &Metrics::get_information_ratio)
      .def("get_maximum_drawdown", &Metrics::get_maximum_drawdown)
      .def("get_calmar_ratio", &Metrics::get_calmar_ratio)
      .def("get_profit_factor", &Metrics::get_profit_factor)
      .def("get_win_rate", &Metrics::get_win_rate)
      .def("get_beta", &Metrics::get_beta)
      .def("get_alpha", &Metrics::get_alpha);

  // strategy
  py::class_<Strategy, std::shared_ptr<Strategy>> strategy_base(m, "Strategy");
  py::class_<SMAStrategy, Strategy, std::shared_ptr<SMAStrategy>>(m,
                                                                  "SMAStrategy")
      .def(py::init<std::int64_t, int, int>())
      .def("get_warmup_days", &SMAStrategy::get_warmup_days);

  // fees
  py::class_<FeeStructure, std::shared_ptr<FeeStructure>> fee_base(
      m, "FeeStructure");
  py::class_<PercentageFee, FeeStructure, std::shared_ptr<PercentageFee>>(
      m, "PercentageFee")
      .def(py::init<double, double, double>());

  py::class_<ShareFlatFee, FeeStructure, std::shared_ptr<ShareFlatFee>>(
      m, "ShareFlatFee")
      .def(py::init<double, double, double>());

  py::class_<OrderFlatFee, FeeStructure, std::shared_ptr<OrderFlatFee>>(
      m, "OrderFlatFee")
      .def(py::init<double>());
}