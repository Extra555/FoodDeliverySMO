#ifndef OPERATOR_H
#define OPERATOR_H

#include "Event.h"
#include <random>

class Operator {
private:
  int operatorId;
  double processingTimeMean;
  std::pair<int, int> currentOrder;
  bool busy;
  double completionTime;
  int processedCount;
  std::mt19937 generator;

public:
  Operator(int id, double mean);

  Event coordinateDelivery(int restaurantId, int orderId, double currentTime);
  Event completeProcessing(double currentTime);
  void reset();

  int getOperatorId() const;
  bool isBusy() const;
  double getCompletionTime() const;
  int getProcessedCount() const;
  std::pair<int, int> getCurrentOrder() const;
};

#endif