#ifndef STATISTICS_H
#define STATISTICS_H

#include <vector>

struct RestaurantStats {
  int generated = 0;
  int processed = 0;
  int rejected = 0;
  double totalWaitTime = 0;
  double totalProcessTime = 0;
};

class Statistics {
private:
  std::vector<RestaurantStats> restaurantsStats;
  int totalOrders;
  int totalProcessed;
  int totalRejected;
  double currentTime;

public:
  Statistics(int numRestaurants);

  void orderGenerated(int restaurantId);
  void orderProcessed(int restaurantId, double waitTime, double processTime);
  void orderRejected(int restaurantId);

  double getRejectionRate() const;
  double getRestaurantRejectionRate(int restaurantId) const;
  double getAvgWaitTime(int restaurantId) const;
  double getAvgProcessTime(int restaurantId) const;

  void printSummary() const;
  void reset();

  
  int getTotalOrders() const;
  int getTotalProcessed() const;
  int getTotalRejected() const;
  const RestaurantStats& getRestaurantStats(int restaurantId) const;
};

#endif