#ifndef DISPATCHER_H
#define DISPATCHER_H

#include "Event.h"
#include "Buffer.h"
#include "Operator.h"
#include "RestaurantSource.h"
#include "Statistics.h"
#include <vector>
#include <optional>

class PlacementDispatcher {
private:
  Buffer& buffer;
  Statistics& statistics;

public:
  PlacementDispatcher(Buffer& buf, Statistics& stats);
  std::vector<Event> handleNewOrder(const std::vector<RestaurantSource>& restaurants,
    const std::vector<Operator>& operators,
    double currentTime,
    int restaurantId,
    int orderId);
  Operator* findFreeOperator(const std::vector<Operator>& operators);
};

class SelectionDispatcher {
private:
  Buffer& buffer;
  std::optional<int> currentPackageRestaurant;
  std::vector<std::pair<int, Order>> packageOrders;

public:
  SelectionDispatcher(Buffer& buf);
  std::optional<Event> selectNextOrder(double currentTime);
  std::pair<int, int> getCurrentPackageInfo() const;
  void reset();
  void updatePackage();
};

#endif
