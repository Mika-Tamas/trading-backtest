#include "circular_buffer.hpp"
#include <gtest/gtest.h>

TEST(CircularBufferTest, Initialization) {
  CircularBuffer<int> cb(5);
  EXPECT_EQ(cb.get_size(), 0);
}

TEST(CircularBufferTest, PushAndGet) {
  CircularBuffer<int> cb(3);
  cb.push(10);
  cb.push(20);

  EXPECT_EQ(cb.get_size(), 2);
  EXPECT_EQ(cb.get_newest(), 20);
  EXPECT_EQ(cb.get_oldest(), 10);
}

TEST(CircularBufferTest, WrapAround) {
  CircularBuffer<int> cb(3);
  cb.push(1);
  cb.push(2);
  cb.push(3);
  cb.push(4);

  EXPECT_EQ(cb.get_size(), 3);
  EXPECT_EQ(cb.get_newest(), 4);
  EXPECT_EQ(cb.get_oldest(), 2);

  EXPECT_EQ(cb.get_prev(0), 4);
  EXPECT_EQ(cb.get_prev(1), 3);
  EXPECT_EQ(cb.get_prev(2), 2);
}

TEST(CircularBufferTest, PrevOutOfBounds) {
  CircularBuffer<int> cb(3);
  EXPECT_EQ(cb.get_oldest(), 0);
  EXPECT_EQ(cb.get_newest(), 0);
  EXPECT_EQ(cb.get_prev(0), 0);
  EXPECT_EQ(cb.get_prev(-1), 0);

  cb.push(10);
  EXPECT_EQ(cb.get_prev(1), 0);
  EXPECT_EQ(cb.get_prev(-1), 0);
  EXPECT_EQ(cb.get_prev(100), 0);
}

TEST(CircularBufferTest, CapacityOne) {
  CircularBuffer<int> cb(1);
  EXPECT_EQ(cb.get_size(), 0);

  cb.push(42);
  EXPECT_EQ(cb.get_size(), 1);
  EXPECT_EQ(cb.get_newest(), 42);
  EXPECT_EQ(cb.get_oldest(), 42);
  EXPECT_EQ(cb.get_prev(0), 42);
  EXPECT_EQ(cb.get_prev(1), 0);

  cb.push(99);
  EXPECT_EQ(cb.get_size(), 1);
  EXPECT_EQ(cb.get_newest(), 99);
  EXPECT_EQ(cb.get_oldest(), 99);
  EXPECT_EQ(cb.get_prev(0), 99);
}

TEST(CircularBufferTest, MultipleFullWrapAroundOverwrites) {
  CircularBuffer<int> cb(4);
  for (int i = 1; i <= 15; ++i) {
    cb.push(i);
  }

  EXPECT_EQ(cb.get_size(), 4);
  EXPECT_EQ(cb.get_newest(), 15);
  EXPECT_EQ(cb.get_oldest(), 12);
  EXPECT_EQ(cb.get_prev(0), 15);
  EXPECT_EQ(cb.get_prev(1), 14);
  EXPECT_EQ(cb.get_prev(2), 13);
  EXPECT_EQ(cb.get_prev(3), 12);
  EXPECT_EQ(cb.get_prev(4), 0);
}

TEST(CircularBufferTest, RunningSumAndAverageDriftOverThousandsOfInsertions) {
  constexpr int kWindow = 20;
  constexpr int kIterations = 10000;
  CircularBuffer<double> cb(kWindow);

  double running_sum = 0.0;
  double comp = 0.0;

  for (int i = 1; i <= kIterations; ++i) {
    double val = (i % 2 == 0 ? 1000.0 : 0.0125) + (i % 17) * 0.375;
    double removed = (cb.get_size() == kWindow) ? cb.get_oldest() : 0.0;

    // Kahan update
    double y_sub = -removed - comp;
    double t_sub = running_sum + y_sub;
    comp = (t_sub - running_sum) - y_sub;
    running_sum = t_sub;

    double y_add = val - comp;
    double t_add = running_sum + y_add;
    comp = (t_add - running_sum) - y_add;
    running_sum = t_add;

    cb.push(val);
  }

  ASSERT_EQ(cb.get_size(), kWindow);
  double direct_sum = 0.0;
  for (int offset = 0; offset < kWindow; ++offset) {
    direct_sum += cb.get_prev(offset);
  }

  EXPECT_NEAR(running_sum, direct_sum, 1e-9);
  EXPECT_NEAR(running_sum / kWindow, direct_sum / kWindow, 1e-10);
}
