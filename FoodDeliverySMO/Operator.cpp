#define _CRT_SECURE_NO_WARNINGS
#include "Operator.h"
#include <cmath>
#include <limits>

Operator::Operator(int id, double mean)
  : operatorId(id), processingTimeMean(mean), busy(false),
  completionTime(std::numeric_limits<double>::infinity()),
  processedCount(0), generator(std::random_device{}()) {}

Event Operator::coordinateDelivery(int restaurantId, int orderId, double currentTime) {
  busy = true;
  currentOrder = { restaurantId, orderId };

  std::uniform_real_distribution<double> dist(0.0, 1.0);
  double processingTime = -std::log(1 - dist(generator)) * processingTimeMean;
  completionTime = currentTime + processingTime;
  processedCount++;

  return Event(EventType::DELIVERY_COORDINATION_START, currentTime, restaurantId, orderId, operatorId);
}

Event Operator::completeProcessing(double currentTime) {
  Event event(EventType::OPERATOR_FREE, currentTime,
    currentOrder.first, currentOrder.second, operatorId);

  busy = false;
  currentOrder = { -1, -1 };
  completionTime = std::numeric_limits<double>::infinity();

  return event;
}

void Operator::reset() {
  busy = false;
  currentOrder = { -1, -1 };
  completionTime = std::numeric_limits<double>::infinity();
  processedCount = 0;
}

int Operator::getOperatorId() const { return operatorId; }
bool Operator::isBusy() const { return busy; }
double Operator::getCompletionTime() const { return completionTime; }
int Operator::getProcessedCount() const { return processedCount; }
std::pair<int, int> Operator::getCurrentOrder() const { return currentOrder; }