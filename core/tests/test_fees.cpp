#include "fee_structure.h"
#include "order_flat_fee.h"
#include "percentage_fee.h"
#include "share_flat_fee.h"
#include <gtest/gtest.h>
#include <memory>
#include <vector>

TEST(PercentageFeeTest, CalculatePercentageFee) {
  PercentageFee fee(0.01, 0.0, 0.0);
  EXPECT_DOUBLE_EQ(fee.calculate_fee(100.0, 10), 10.0);
}

TEST(PercentageFeeTest, QuantityFromCashPercentageFee) {
  PercentageFee fee(0.01, 0.0, 0.0);
  EXPECT_EQ(fee.quantity_from_cash(1000.0, 100.0), 9);
}

TEST(ShareFlatFeeTest, CalculateShareFlatFee) {
  ShareFlatFee fee(0.05, 0.0, 0.0);
  EXPECT_DOUBLE_EQ(fee.calculate_fee(100.0, 10), 0.5);
}

TEST(ShareFlatFeeTest, QuantityFromCashShareFlatFee) {
  ShareFlatFee fee(0.05, 0.0, 0.0);
  EXPECT_EQ(fee.quantity_from_cash(1000.0, 100.0), 9);
}

TEST(OrderFlatFeeTest, CalculateOrderFlatFee) {
  OrderFlatFee fee(5.0);
  EXPECT_DOUBLE_EQ(fee.calculate_fee(100.0, 10), 5.0);
}

TEST(OrderFlatFeeTest, QuantityFromCashOrderFlatFee) {
  OrderFlatFee fee(5.0);
  EXPECT_EQ(fee.quantity_from_cash(1000.0, 100.0), 9);
}

TEST(FeeEdgeCasesTest, ZeroQuantityAndNegativeInvalidInputs) {
  PercentageFee pct_with_min(0.01, 5.0, 50.0);
  ShareFlatFee share_with_min(0.05, 2.0, 20.0);
  OrderFlatFee flat_order(5.0);

  std::vector<std::shared_ptr<FeeStructure>> models = {
      std::make_shared<PercentageFee>(pct_with_min),
      std::make_shared<ShareFlatFee>(share_with_min),
      std::make_shared<OrderFlatFee>(flat_order),
  };

  for (const auto &model : models) {
    EXPECT_DOUBLE_EQ(model->calculate_fee(100.0, 0), 0.0);
    EXPECT_DOUBLE_EQ(model->calculate_fee(100.0, -5), 0.0);
    EXPECT_DOUBLE_EQ(model->calculate_fee(-100.0, 10), 0.0);
    EXPECT_EQ(model->quantity_from_cash(0.0, 100.0), 0);
    EXPECT_EQ(model->quantity_from_cash(-500.0, 100.0), 0);
    EXPECT_EQ(model->quantity_from_cash(1000.0, 0.0), 0);
    EXPECT_EQ(model->quantity_from_cash(1000.0, -10.0), 0);
    EXPECT_EQ(model->quantity_from_cash(1.0, 100.0), 0);
  }

  EXPECT_EQ(share_with_min.quantity_from_cash(101.0, 100.0), 0);
  EXPECT_EQ(pct_with_min.quantity_from_cash(102.0, 100.0), 0);
  EXPECT_EQ(flat_order.quantity_from_cash(5.0, 100.0), 0);
  EXPECT_EQ(flat_order.quantity_from_cash(4.0, 100.0), 0);
}

TEST(FeeEdgeCasesTest, HighFrequencySmallOrdersAndPolymorphicDispatch) {
  std::vector<std::unique_ptr<FeeStructure>> models;
  models.push_back(std::make_unique<OrderFlatFee>(5.0));
  models.push_back(std::make_unique<PercentageFee>(0.01, 1.0, 25.0));
  models.push_back(std::make_unique<ShareFlatFee>(0.05, 0.50, 10.0));

  constexpr int kOrders = 1000;
  std::vector<double> totals(models.size(), 0.0);

  for (int i = 0; i < kOrders; ++i) {
    for (size_t m = 0; m < models.size(); ++m) {
      totals[m] += models[m]->calculate_fee(10.0, 1);
    }
  }

  EXPECT_DOUBLE_EQ(totals[0], 5000.0);
  // Clamped to min_fee ($1.00 and $0.50)
  EXPECT_DOUBLE_EQ(totals[1], 1000.0);
  EXPECT_DOUBLE_EQ(totals[2], 500.0);

  EXPECT_DOUBLE_EQ(models[1]->calculate_fee(1000.0, 100), 25.0);
  EXPECT_DOUBLE_EQ(models[2]->calculate_fee(100.0, 1000), 10.0);
}

TEST(FeeEdgeCasesTest, ClosedFormQuantityWithLargeMinFeeAndTinyPrice) {
  PercentageFee pct(0.001, 500.0, 1000.0);
  ShareFlatFee share(0.00001, 500.0, 1000.0);

  EXPECT_EQ(pct.quantity_from_cash(1000.0, 0.0001), 5000000);
  EXPECT_EQ(share.quantity_from_cash(1000.0, 0.0001), 5000000);

  PercentageFee pct_capped(0.5, 1.0, 10.0);
  ShareFlatFee share_capped(5.0, 1.0, 10.0);
  EXPECT_EQ(pct_capped.quantity_from_cash(1000.0, 10.0), 99);
  EXPECT_EQ(share_capped.quantity_from_cash(1000.0, 10.0), 99);
}
