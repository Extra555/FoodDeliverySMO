#define _CRT_SECURE_NO_WARNINGS
#include "Event.h"
#include <string>

Event::Event(EventType t, double tm, int restId, int ordId, int opId, int bufPos, double wait)
  : type(t), time(tm), restaurantId(restId), orderId(ordId),
  operatorId(opId), bufferPosition(bufPos), waitTime(wait) {}

std::string Event::toString() const {
  std::string typeStr;
  switch (type) {
  case EventType::ORDER_GENERATED: typeStr = "ORDER_GENERATED"; break;
  case EventType::ORDER_TO_BUFFER: typeStr = "ORDER_TO_BUFFER"; break;
  case EventType::ORDER_TO_OPERATOR: typeStr = "ORDER_TO_OPERATOR"; break;
  case EventType::DELIVERY_COORDINATION_START: typeStr = "DELIVERY_COORDINATION_START"; break;
  case EventType::OPERATOR_FREE: typeStr = "OPERATOR_FREE"; break;
  case EventType::ORDER_REJECTED: typeStr = "ORDER_REJECTED"; break;
  case EventType::ORDER_SELECTED: typeStr = "ORDER_SELECTED"; break;
  }

  return "Event{type=" + typeStr + ", time=" + std::to_string(time) +
    ", restaurant=" + std::to_string(restaurantId) + ", order=" + std::to_string(orderId) +
    ", operator=" + std::to_string(operatorId) + ", bufferPos=" + std::to_string(bufferPosition) + "}";
}