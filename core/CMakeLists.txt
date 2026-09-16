cmake_minimum_required(VERSION 3.14)
project(backtest_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python COMPONENTS Interpreter Development REQUIRED)

execute_process(
    COMMAND "${Python_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

find_package(pybind11 REQUIRED)

add_library(backtest_core_objs OBJECT
    engine/src/Portfolio.cpp
    engine/src/Backtester.cpp
    engine/src/Metrics.cpp
    strategies/SMA_strategy.cpp
    fees/src/Percentage_fee.cpp
    fees/src/Share_flat_fee.cpp
    fees/src/Order_flat_fee.cpp
)

target_include_directories(backtest_core_objs PUBLIC
    engine/include
    strategies
)

set_property(TARGET backtest_core_objs PROPERTY POSITION_INDEPENDENT_CODE ON)

pybind11_add_module(backtest_core THIN_LTO
    engine/src/Bindings.cpp
)

target_link_libraries(backtest_core PRIVATE backtest_core_objs)

if(MINGW)
    target_link_options(backtest_core PRIVATE "-static")
endif()



set(CMAKE_TLS_VERIFY OFF)
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()
add_subdirectory(tests)
