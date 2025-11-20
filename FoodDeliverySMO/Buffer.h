#ifndef BUFFER_H
#define BUFFER_H

#include "Order.h"
#include <vector>
#include <optional>

class Buffer {
private:
  int capacity;
  std::vector<std::optional<Order>> orders;
  int currentSize;

public:
  Buffer(int cap);

  bool addOrder(int restaurantId, int orderId, double currentTime);
  std::optional<Order> removeOrder(int position);
  std::vector<std::pair<int, Order>> getOrdersByRestaurant(int restaurantId) const;
  std::vector<Order> getNextPacket(int restaurantId) const;
  std::optional<int> getFirstOrderPosition() const;

  
  bool isFull() const;
  bool isEmpty() const;
  int getSize() const;
  int getCapacity() const;
  const std::vector<std::optional<Order>>& getOrders() const;

  void clear();
};

#endif