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
  cb.push(10);
  EXPECT_EQ(cb.get_prev(1), 0);
}
