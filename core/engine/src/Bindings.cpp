#include <memory>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "../../strategies/SMA_strategy.h"
#include "../../strategies/Strategy.h"
#include "../include/Backtester.h"
#include "../include/Portfolio.h"
#include "../include/Types.h"

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
      .def_readwrite("realized_pnl", &Trade::realized_pnl);
  py::class_<Position>(m, "Position")
      .def_readwrite("symbol", &Position::symbol)
      .def_readwrite("quantity", &Position::quantity)
      .def_readwrite("average_entry_price", &Position::average_entry_price)
      .def_readwrite("entry_time", &Position::entry_time);
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
      .def(py::init<double, std::shared_ptr<Strategy>>())
      .def("run", &Backtester::run)
      .def("get_portfolio", &Backtester::get_portfolio)
      .def("get_equity_curve", &Backtester::get_equity_curve)
      .def("get_timestamps", &Backtester::get_timestamps)
      .def("get_benchmark_curve", &Backtester::get_benchmark_curve);
  py::class_<Portfolio>(m, "Portfolio")
      .def("get_cash", &Portfolio::get_cash)
      .def("get_equity", &Portfolio::get_equity)
      .def("get_trade_history", &Portfolio::get_trade_history)
      .def("get_positions", &Portfolio::get_positions);

  // strategy
  py::class_<Strategy, std::shared_ptr<Strategy>> strategy_base(m, "Strategy");
  py::class_<SMA_strategy, Strategy, std::shared_ptr<SMA_strategy>>(
      m, "SMA_strategy")
      .def(py::init<int, int>());
}