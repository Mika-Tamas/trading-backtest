#include "../../fees/include/Order_flat_fee.h"
#include "../../fees/include/Percentage_fee.h"
#include "../../fees/include/Share_flat_fee.h"
#include <gtest/gtest.h>

TEST(PercentageFeeTest, CalculatePercentageFee) {
  Percentage_fee fee(0.01, 0.0, 0.0);
  EXPECT_DOUBLE_EQ(fee.calculate_fee(100.0, 10), 10.0);
}

TEST(PercentageFeeTest, QuantityFromCashPercentageFee) {
  Percentage_fee fee(0.01, 0.0, 0.0);
  EXPECT_EQ(fee.quantity_from_cash(1000.0, 100.0), 9);
}

TEST(ShareFlatFeeTest, CalculateShareFlatFee) {
  Share_flat_fee fee(0.05, 0.0, 0.0);
  EXPECT_DOUBLE_EQ(fee.calculate_fee(100.0, 10), 0.5);
}

TEST(ShareFlatFeeTest, QuantityFromCashShareFlatFee) {
  Share_flat_fee fee(0.05, 0.0, 0.0);
  EXPECT_EQ(fee.quantity_from_cash(1000.0, 100.0), 9);
}

TEST(OrderFlatFeeTest, CalculateOrderFlatFee) {
  Order_flat_fee fee(5.0);
  EXPECT_DOUBLE_EQ(fee.calculate_fee(100.0, 10), 5.0);
}

TEST(OrderFlatFeeTest, QuantityFromCashOrderFlatFee) {
  Order_flat_fee fee(5.0);
  EXPECT_EQ(fee.quantity_from_cash(1000.0, 100.0), 9);
}
