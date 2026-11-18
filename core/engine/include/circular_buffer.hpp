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
      : size(0), head(-1), items(max_capacity > 0 ? max_capacity : 0),
        capacity(max_capacity > 0 ? max_capacity : 0) {}

  ~CircularBuffer() = default;
  std::vector<T> get_all_items() const {
    std::vector<T> result;
    result.reserve(size);
    for (int offset = size - 1; offset >= 0; --offset) {
      result.push_back(get_prev(offset));
    }
    return result;
  }
  int get_size() const { return size; }
  T get_oldest() const {
    if (size == 0) {
      return T{};
    }
    return get_prev(size - 1);
  }
  T get_newest() const {
    if (size == 0) {
      return T{};
    }
    return get_prev(0);
  }
  T get_prev(int offset) const {

    if (offset < 0 || offset >= size) {
      return T{};
    }

    int index = head - offset;
    if (index < 0) {
      index = capacity + index;
    }

    return items[index];
  }
  void push(T elem) {
    if (capacity <= 0) {
      return;
    }
    head++;
    if (head >= capacity)
      head = 0;

    items[head] = elem;
    if (capacity > size) {
      size++;
    }
  }
};