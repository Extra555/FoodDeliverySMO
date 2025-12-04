#ifndef SMO_SIMULATOR_H
#define SMO_SIMULATOR_H

#include <queue>
#include <vector>
#include <optional>

#include "Event.h"
#include "RestaurantSource.h"
#include "Operator.h"
#include "Buffer.h"
#include "Dispatcher.h"
#include "Statistics.h"


struct EventCompare {
  bool operator()(const Event& a, const Event& b) const {
    return a.time > b.time;
  }
};

class SMOSimulator
{
private:
  std::vector<RestaurantSource> restaurants;
  std::vector<Operator> operators;
  Buffer buffer;
  PlacementDispatcher placementDispatcher;
  SelectionDispatcher selectionDispatcher;
  Statistics statistics;

  std::priority_queue<Event, std::vector<Event>, EventCompare> eventCalendar;

  double currentTime;
  int stepCount;

public:
  SMOSimulator(int restaurantCount,
    int operatorCount,
    int bufferCapacity,
    double arrivalMean,
    double operatorMean);

  void initializeSimulation(double untilTime);

  bool step();

  void printCurrentState() const;
  void printEventCalendar() const;

  double getCurrentTime() const;
  int getStepCount() const;
  const Statistics& getStatistics() const;

private:
  void scheduleEvent(const Event& ev);
  void scheduleInitialEvents();
  bool handleEvent();
};

#endif
