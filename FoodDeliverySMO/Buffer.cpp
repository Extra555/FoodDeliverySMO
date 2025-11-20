#define _CRT_SECURE_NO_WARNINGS
#include "Buffer.h"
#include <algorithm>

Buffer::Buffer(int cap) : capacity(cap), currentSize(0) {
  orders.resize(capacity);
}

bool Buffer::addOrder(int restaurantId, int orderId, double currentTime) {
  if (isFull()) {
    return false;
  }

  // Находим первую свободную позицию
  for (int i = 0; i < capacity; i++) {
    if (!orders[i].has_value()) {
      orders[i] = Order(restaurantId, orderId, currentTime);
      currentSize++;
      return true;
    }
  }
  return false;
}

std::optional<Order> Buffer::removeOrder(int position) {
  if (position < 0 || position >= capacity || !orders[position].has_value()) {
    return std::nullopt;
  }

  Order removedOrder = orders[position].value();
  orders[position] = std::nullopt;
  currentSize--;

  // Сдвигаем заказы (Д1ОЗ2)
  for (int i = position; i < capacity - 1; i++) {
    orders[i] = orders[i + 1];
  }
  orders[capacity - 1] = std::nullopt;

  return removedOrder;
}

std::vector<std::pair<int, Order>> Buffer::getOrdersByRestaurant(int restaurantId) const {
  std::vector<std::pair<int, Order>> result;

  for (int i = 0; i < capacity; i++) {
    if (orders[i].has_value() && orders[i]->getRestaurantId() == restaurantId) {
      result.emplace_back(i, orders[i].value());
    }
  }

  return result;
}

std::vector<Order> Buffer::getNextPacket(int restaurantId) const {
  std::vector<Order> packet;
  for (int i = 0; i < capacity; i++) {
    if (orders[i].has_value() && orders[i]->getRestaurantId() == restaurantId) {
      packet.push_back(orders[i].value());
    }
  }
  return packet;
}

std::optional<int> Buffer::getFirstOrderPosition() const {
  for (int i = 0; i < capacity; i++) {
    if (orders[i].has_value()) {
      return i;
    }
  }
  return std::nullopt;
}

bool Buffer::isFull() const { return currentSize >= capacity; }
bool Buffer::isEmpty() const { return currentSize == 0; }
int Buffer::getSize() const { return currentSize; }
int Buffer::getCapacity() const { return capacity; }
const std::vector<std::optional<Order>>& Buffer::getOrders() const { return orders; }

void Buffer::clear() {
  orders = std::vector<std::optional<Order>>(capacity);
  currentSize = 0;
}