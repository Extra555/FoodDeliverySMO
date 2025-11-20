#ifndef RESTAURANT_SOURCE_H
#define RESTAURANT_SOURCE_H

#include "Event.h"
#include "Order.h"

class RestaurantSource {
private:
  int restaurantId;
  double interval;
  int generatedCount;
  double nextGenerationTime;

public:
  RestaurantSource(int id, double interv);

  Event generateOrder(double currentTime);
  void reset();

  int getRestaurantId() const;
  double getInterval() const;
  int getGeneratedCount() const;
  double getNextGenerationTime() const;
};

#endif