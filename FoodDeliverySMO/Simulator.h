#ifndef SIMULATOR_H
#define SIMULATOR_H

#include "Event.h"
#include "RestaurantSource.h"
#include "Buffer.h"
#include "Operator.h"
#include "Statistics.h"
#include "Dispatcher.h"
#include <vector>
#include <queue>
#include <functional>

struct EventComparator {
  bool operator()(const std::pair<double, Event>& a, const std::pair<double, Event>& b) const {
    return a.first > b.first;
  }
};

class SMOSimulator {
private:
  int numRestaurants;
  int numOperators;
  int bufferCapacity;
  double generationInterval;
  double processingTimeMean;

  std::vector<RestaurantSource> restaurants;
  Buffer buffer;
  std::vector<Operator> operators;
  Statistics statistics;

  PlacementDispatcher placementDispatcher;
  SelectionDispatcher selectionDispatcher;

  std::priority_queue<std::pair<double, Event>,
    std::vector<std::pair<double, Event>>,
    EventComparator> eventCalendar;

  double currentTime;
  int stepCount;
  std::vector<Event> stepEvents;

public:
  SMOSimulator(int numRest, int numOp, int bufCap, double genInt, double procMean);

  void initializeSimulation(double simulationTime);
  bool step();
  void runAuto(double simulationTime);

  void printCurrentState() const;
  void printEventCalendar() const;

  double getCurrentTime() const;
  int getStepCount() const;
  const Statistics& getStatistics() const;
  const Buffer& getBuffer() const;
  const std::vector<Operator>& getOperators() const;
  const std::vector<RestaurantSource>& getRestaurants() const;

private:
  std::vector<Event> processEvent(const Event& event);
  Operator* findFreeOperator();
  std::vector<Event> handleOrderGeneratedEvent(const Event& event);
  std::vector<Event> handleOrderToBufferEvent(const Event& event);
  std::vector<Event> handleOrderToOperatorEvent(const Event& event);
  std::vector<Event> handleOrderSelectedEvent(const Event& event);
  std::vector<Event> handleOperatorFreeEvent(const Event& event);
  std::vector<Event> handleDeliveryCoordinationStartEvent(const Event& event);
  
};

#endif