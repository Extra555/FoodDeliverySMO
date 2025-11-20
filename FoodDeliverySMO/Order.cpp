#define _CRT_SECURE_NO_WARNINGS
#include "Order.h"
#include <string>

Order::Order(int restId, int ordId, double time, const std::string& det)
  : restaurantId(restId), orderId(ordId), timestamp(time), details(det) {}

int Order::getRestaurantId() const { return restaurantId; }
int Order::getOrderId() const { return orderId; }
double Order::getTimestamp() const { return timestamp; }
std::string Order::getDetails() const { return details; }

std::string Order::toString() const {
  return "Order{restaurant=" + std::to_string(restaurantId) +
    ", id=" + std::to_string(orderId) +
    ", time=" + std::to_string(timestamp) + "}";
}