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

include(GoogleTest)
gtest_discover_tests(backtest_tests)
