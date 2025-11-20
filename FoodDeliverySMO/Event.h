#ifndef EVENT_H
#define EVENT_H

#include <string>

enum class EventType {
  ORDER_GENERATED,
  ORDER_TO_BUFFER,
  ORDER_TO_OPERATOR,
  DELIVERY_COORDINATION_START,
  OPERATOR_FREE,
  ORDER_REJECTED,
  ORDER_SELECTED
};

struct Event {
  EventType type;
  double time;
  int restaurantId;
  int orderId;
  int operatorId;
  int bufferPosition;
  double waitTime;

  Event(EventType t, double tm, int restId = -1, int ordId = -1,
    int opId = -1, int bufPos = -1, double wait = 0);

  std::string toString() const;
};

#endif