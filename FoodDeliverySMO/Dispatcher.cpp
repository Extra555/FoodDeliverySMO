#define _CRT_SECURE_NO_WARNINGS
#include "Dispatcher.h"
#include <algorithm>
#include <set>
#include <iostream>

PlacementDispatcher::PlacementDispatcher(Buffer& buf, Statistics& stats)
  : buffer(buf), statistics(stats) {}

Operator* PlacementDispatcher::findFreeOperator(const std::vector<Operator>& operators) {
  
  for (int i = 0; i < operators.size(); i++) {
    if (!operators[i].isBusy()) {
      return const_cast<Operator*>(&operators[i]);
    }
  }
  return nullptr;
}

std::vector<Event> PlacementDispatcher::handleNewOrder(const std::vector<RestaurantSource>& restaurants,
  const std::vector<Operator>& operators,
  double currentTime, int restaurantId, int orderId) {
  std::vector<Event> events;

  
  Operator* freeOperator = findFreeOperator(operators);
  if (freeOperator != nullptr) {
    
    events.push_back(Event(EventType::ORDER_TO_OPERATOR, currentTime,
      restaurantId, orderId, freeOperator->getOperatorId()));
  }
  else {
    
    if (buffer.addOrder(restaurantId, orderId, currentTime)) {
      
      int position = -1;
      for (int i = 0; i < buffer.getCapacity(); i++) {
        if (buffer.getOrders()[i].has_value() &&
          buffer.getOrders()[i]->getRestaurantId() == restaurantId &&
          buffer.getOrders()[i]->getOrderId() == orderId) {
          position = i;
          break;
        }
      }
      events.push_back(Event(EventType::ORDER_TO_BUFFER, currentTime,
        restaurantId, orderId, -1, position));
    }
    else {
      
      statistics.orderRejected(restaurantId);
      events.push_back(Event(EventType::ORDER_REJECTED, currentTime, restaurantId, orderId));
    }
  }

  return events;
}

SelectionDispatcher::SelectionDispatcher(Buffer& buf)
  : buffer(buf), currentPackageRestaurant(std::nullopt) {}

void SelectionDispatcher::updatePackage() {
  if (buffer.isEmpty()) {
    currentPackageRestaurant = std::nullopt;
    packageOrders.clear();
    return;
  }

  
  std::set<int> restaurantsInBuffer;
  for (int i = 0; i < buffer.getCapacity(); i++) {
    if (buffer.getOrders()[i].has_value()) {
      restaurantsInBuffer.insert(buffer.getOrders()[i]->getRestaurantId());
    }
  }

  if (!restaurantsInBuffer.empty()) {
    currentPackageRestaurant = *restaurantsInBuffer.begin();
    packageOrders = buffer.getOrdersByRestaurant(currentPackageRestaurant.value());
  }
  else {
    currentPackageRestaurant = std::nullopt;
    packageOrders.clear();
  }
}

std::optional<Event> SelectionDispatcher::selectNextOrder(const std::vector<Operator>& operators, double currentTime) {
  if (buffer.isEmpty()) {
    currentPackageRestaurant = std::nullopt;
    packageOrders.clear();
    return std::nullopt;
  }

  
  updatePackage();

  
  if (currentPackageRestaurant.has_value() && !packageOrders.empty()) {
    
    int position = packageOrders[0].first;
    Order order = packageOrders[0].second;

    
    packageOrders.erase(packageOrders.begin());

    
    return Event(EventType::ORDER_SELECTED, currentTime,
      order.getRestaurantId(), order.getOrderId(), -1, position,
      currentTime - order.getTimestamp());
  }

  return std::nullopt;
}

std::pair<int, int> SelectionDispatcher::getCurrentPackageInfo() const {
  if (currentPackageRestaurant.has_value()) {
    return { currentPackageRestaurant.value(), packageOrders.size() };
  }
  return { -1, 0 };
}

void SelectionDispatcher::reset() {
  currentPackageRestaurant = std::nullopt;
  packageOrders.clear();
}