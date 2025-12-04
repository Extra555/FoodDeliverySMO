#define _CRT_SECURE_NO_WARNINGS
#include "Dispatcher.h"
#include <set>
#include <iostream>

PlacementDispatcher::PlacementDispatcher(Buffer& buf, Statistics& stats)
  : buffer(buf), statistics(stats) {}

Operator* PlacementDispatcher::findFreeOperator(const std::vector<Operator>& operators) {
  for (int i = 0; i < (int)operators.size(); i++) {
    if (!operators[i].isBusy()) {
      return const_cast<Operator*>(&operators[i]);
    }
  }
  return nullptr;
}

std::vector<Event> PlacementDispatcher::handleNewOrder(
  const std::vector<RestaurantSource>& restaurants,
  const std::vector<Operator>& operators,
  double currentTime, int restaurantId, int orderId)
{
  std::vector<Event> events;

  Operator* freeOp = findFreeOperator(operators);

  if (freeOp != nullptr) {

    events.push_back(Event(
      EventType::ORDER_TO_OPERATOR,
      currentTime,
      restaurantId,
      orderId,
      freeOp->getOperatorId()
    ));
  }
  else {
    if (buffer.addOrder(restaurantId, orderId, currentTime)) {

      int pos = -1;
      for (int i = 0; i < buffer.getCapacity(); i++) {
        if (buffer.getOrders()[i].has_value() &&
          buffer.getOrders()[i]->getRestaurantId() == restaurantId &&
          buffer.getOrders()[i]->getOrderId() == orderId)
        {
          pos = i;
          break;
        }
      }

      events.push_back(Event(
        EventType::ORDER_TO_BUFFER,
        currentTime,
        restaurantId,
        orderId,
        -1,
        pos
      ));
    }
    else {
      statistics.orderRejected(restaurantId);

      events.push_back(Event(
        EventType::ORDER_REJECTED,
        currentTime,
        restaurantId,
        orderId
      ));
    }
  }

  return events;
}



SelectionDispatcher::SelectionDispatcher(Buffer& buf)
  : buffer(buf), currentPackageRestaurant(std::nullopt) {}

void SelectionDispatcher::reset() {
  currentPackageRestaurant = std::nullopt;
  packageOrders.clear();
}

void SelectionDispatcher::updatePackage() {
  if (buffer.isEmpty()) {
    currentPackageRestaurant = std::nullopt;
    packageOrders.clear();
    return;
  }

  if (currentPackageRestaurant.has_value()) {
    auto orders = buffer.getOrdersByRestaurant(currentPackageRestaurant.value());
    if (!orders.empty()) {
      packageOrders = std::move(orders);
      return;
    }
  }

  std::set<int> restaurants;

  for (int i = 0; i < buffer.getCapacity(); i++) {
    if (buffer.getOrders()[i].has_value()) {
      restaurants.insert(buffer.getOrders()[i]->getRestaurantId());
    }
  }

  if (restaurants.empty()) {
    currentPackageRestaurant = std::nullopt;
    packageOrders.clear();
    return;
  }

  currentPackageRestaurant = *restaurants.begin();
  packageOrders = buffer.getOrdersByRestaurant(currentPackageRestaurant.value());
}

std::optional<Event> SelectionDispatcher::selectNextOrder(double currentTime) {

  if (buffer.isEmpty())
    return std::nullopt;

  if (packageOrders.empty())
    updatePackage();

  if (packageOrders.empty())
    return std::nullopt;

  auto [pos, order] = packageOrders.front();
  packageOrders.erase(packageOrders.begin());

  return Event(
    EventType::ORDER_SELECTED,
    currentTime,
    order.getRestaurantId(),
    order.getOrderId(),
    -1,
    pos,
    currentTime - order.getTimestamp()
  );
}

std::pair<int, int> SelectionDispatcher::getCurrentPackageInfo() const {
  if (currentPackageRestaurant.has_value())
    return { currentPackageRestaurant.value(), (int)packageOrders.size() };

  return { -1, 0 };
}
