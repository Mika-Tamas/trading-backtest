#pragma once

#include <vector>

template <typename T> class CircularBuffer {
private:
  std::vector<T> items;
  int head;
  int size;
  int capacity;

public:
  CircularBuffer(int max_capacity)
      : size(0), head(-1), items(max_capacity), capacity(max_capacity) {}

  ~CircularBuffer() = default;
  std::vector<T> get_all_items() const { return items; }
  int get_size() const { return size; }
  T get_oldest() const { return get_prev(size - 1); }
  T get_newest() const { return get_prev(0); }
  T get_prev(int offset) const {

    if (offset >= size) {
      return T{};
    }

    int index = head - offset;
    if (index < 0) {
      index = capacity + index;
    }

    return items[index];
  }
  void push(T elem) {
    head++;
    if (head >= capacity)
      head = 0;

    items[head] = elem;
    if (capacity > size) {
      size++;
    }
  }
};