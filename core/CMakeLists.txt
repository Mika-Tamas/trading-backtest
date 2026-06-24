cmake_minimum_required(VERSION 3.12)
project(backtest_core LANGUAGES CXX)


#C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Python COMPONENTS Interpreter Development REQUIRED) # python.exe

execute_process( #path to pybind
    COMMAND "${Python_EXECUTABLE}" -c "import pybind11; print(pybind11.get_cmake_dir())"
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
)

find_package(pybind11 REQUIRED)

pybind11_add_module(backtest_core THIN_LTO
    engine/src/Bindings.cpp
    engine/src/Portfolio.cpp
    engine/src/Backtester.cpp
    strategies/SMA_strategy.cpp
)

target_include_directories(backtest_core PRIVATE
    engine/include
    strategies
)

if(MINGW)
    target_link_options(backtest_core PRIVATE "-static")
endif()
