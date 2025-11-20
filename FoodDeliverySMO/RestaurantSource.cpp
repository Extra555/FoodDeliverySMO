#define _CRT_SECURE_NO_WARNINGS
#include "RestaurantSource.h"

RestaurantSource::RestaurantSource(int id, double interv)
  : restaurantId(id), interval(interv), generatedCount(0), nextGenerationTime(0) {}

Event RestaurantSource::generateOrder(double currentTime) {
  
  double time = nextGenerationTime;
  int orderId = generatedCount;
  generatedCount++;

  
  nextGenerationTime = time + interval;

  return Event(EventType::ORDER_GENERATED, time, restaurantId, orderId);
}

void RestaurantSource::reset() {
  generatedCount = 0;
  nextGenerationTime = 0;
}

int RestaurantSource::getRestaurantId() const { return restaurantId; }
double RestaurantSource::getInterval() const { return interval; }
int RestaurantSource::getGeneratedCount() const { return generatedCount; }
double RestaurantSource::getNextGenerationTime() const { return nextGenerationTime; }