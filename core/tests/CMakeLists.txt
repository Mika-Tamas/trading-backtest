add_executable(backtest_tests
    test_circular_buffer.cpp
    test_portfolio.cpp
    test_fees.cpp
)

target_link_libraries(backtest_tests
    PRIVATE
        backtest_core_objs
        GTest::gtest_main
)

# Also link threading if necessary (gtest usually handles it but to be safe)
find_package(Threads REQUIRED)
target_link_libraries(backtest_tests PRIVATE Threads::Threads)

include(GoogleTest)
gtest_discover_tests(backtest_tests)
