#define _CRT_SECURE_NO_WARNINGS
#include "Statistics.h"
#include <iostream>
#include <iomanip>
#include <limits>

Statistics::Statistics(int numRestaurants)
  : restaurantsStats(numRestaurants), totalOrders(0), totalProcessed(0),
  totalRejected(0), currentTime(0) {}

void Statistics::orderGenerated(int restaurantId) {
  restaurantsStats[restaurantId].generated++;
  totalOrders++;
}

void Statistics::orderProcessed(int restaurantId, double waitTime, double processTime) {
  restaurantsStats[restaurantId].processed++;
  restaurantsStats[restaurantId].totalWaitTime += waitTime;
  restaurantsStats[restaurantId].totalProcessTime += processTime;
  totalProcessed++;
}

void Statistics::orderRejected(int restaurantId) {
  restaurantsStats[restaurantId].rejected++;
  totalRejected++;
}

double Statistics::getRejectionRate() const {
  if (totalOrders == 0) return 0;
  return static_cast<double>(totalRejected) / totalOrders;
}

double Statistics::getRestaurantRejectionRate(int restaurantId) const {
  const RestaurantStats& stats = restaurantsStats[restaurantId];
  if (stats.generated == 0) return 0;
  return static_cast<double>(stats.rejected) / stats.generated;
}

double Statistics::getAvgWaitTime(int restaurantId) const {
  const RestaurantStats& stats = restaurantsStats[restaurantId];
  if (stats.processed == 0) return 0;
  return stats.totalWaitTime / stats.processed;
}

double Statistics::getAvgProcessTime(int restaurantId) const {
  const RestaurantStats& stats = restaurantsStats[restaurantId];
  if (stats.processed == 0) return 0;
  return stats.totalProcessTime / stats.processed;
}

void Statistics::printSummary() const {
  std::cout << "\n" << std::string(80, '=') << "\n";
  std::cout << "СТАТИСТИКА СИСТЕМЫ\n";
  std::cout << std::string(80, '=') << "\n";
  std::cout << "Всего заказов: " << totalOrders << "\n";
  std::cout << "Обработано: " << totalProcessed << "\n";
  std::cout << "Отклонено: " << totalRejected << "\n";
  std::cout << "Процент отказа: " << std::fixed << std::setprecision(2) << (getRejectionRate() * 100) << "%\n";

  std::cout << "\nПо ресторанам:\n";
  for (size_t i = 0; i < restaurantsStats.size(); i++) {
    const RestaurantStats& stats = restaurantsStats[i];
    std::cout << "Ресторан " << i << ": сгенерировано=" << stats.generated
      << ", обработано=" << stats.processed
      << ", отклонено=" << stats.rejected
      << " (" << std::fixed << std::setprecision(2) << (getRestaurantRejectionRate(i) * 100) << "%)\n";
  }
}

void Statistics::reset() {
  for (auto& stats : restaurantsStats) {
    stats = RestaurantStats();
  }
  totalOrders = 0;
  totalProcessed = 0;
  totalRejected = 0;
  currentTime = 0;
}

int Statistics::getTotalOrders() const { return totalOrders; }
int Statistics::getTotalProcessed() const { return totalProcessed; }
int Statistics::getTotalRejected() const { return totalRejected; }
const RestaurantStats& Statistics::getRestaurantStats(int restaurantId) const { return restaurantsStats[restaurantId]; }