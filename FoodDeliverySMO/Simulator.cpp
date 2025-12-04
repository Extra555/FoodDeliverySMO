#define _CRT_SECURE_NO_WARNINGS
#include "Simulator.h"
#include <iostream>
#include <iomanip>


SMOSimulator::SMOSimulator(int restaurantCount, int operatorCount,
  int bufferCapacity, double arrivalMean,
  double operatorMean)
  : buffer(bufferCapacity),
  placementDispatcher(buffer, statistics),
  selectionDispatcher(buffer),
  currentTime(0),
  stepCount(0),
  statistics(restaurantCount)
{
  restaurants.reserve(restaurantCount);
  for (int i = 0; i < restaurantCount; i++)
    restaurants.emplace_back(i, arrivalMean);

  operators.reserve(operatorCount);
  for (int i = 0; i < operatorCount; i++)
    operators.emplace_back(i, operatorMean);
}


void SMOSimulator::initializeSimulation(double untilTime)
{
  currentTime = 0;
  stepCount = 0;

  statistics.reset();
  buffer.clear();
  selectionDispatcher.reset();

  while (!eventCalendar.empty())
    eventCalendar.pop();

  scheduleInitialEvents();
}


void SMOSimulator::scheduleInitialEvents()
{
  for (auto& r : restaurants)
    scheduleEvent(r.generateOrder(0));
}

void SMOSimulator::scheduleEvent(const Event& ev)
{
  eventCalendar.push(ev);
}


bool SMOSimulator::handleEvent()
{
  if (eventCalendar.empty())
    return false;

  Event ev = eventCalendar.top();
  eventCalendar.pop();

  currentTime = ev.time;
  stepCount++;

  switch (ev.type)
  {
  case EventType::ORDER_GENERATED:
  {
    statistics.orderGenerated(ev.restaurantId);

    auto events = placementDispatcher.handleNewOrder(
      restaurants, operators, currentTime,
      ev.restaurantId, ev.orderId);

    for (auto& e : events)
      scheduleEvent(e);

    scheduleEvent(
      restaurants[ev.restaurantId].generateOrder(currentTime));

    break;
  }

  case EventType::ORDER_TO_OPERATOR:
  {
    int op = ev.operatorId;
    auto e = operators[op].coordinateDelivery(
      ev.restaurantId, ev.orderId, currentTime);
    scheduleEvent(e);
    break;
  }

  case EventType::OPERATOR_FREE:
  {
    int op = ev.operatorId;
    operators[op].completeProcessing(currentTime);

    auto next = selectionDispatcher.selectNextOrder(currentTime);
    if (next.has_value())
    {
      auto e = operators[op].coordinateDelivery(
        next->restaurantId, next->orderId, currentTime);
      scheduleEvent(e);
    }
    break;
  }

  case EventType::ORDER_REJECTED:
    statistics.orderRejected(ev.restaurantId);
    break;

  case EventType::ORDER_TO_BUFFER:
  case EventType::DELIVERY_COORDINATION_START:
  default:
    break;
  }

  return true;
}


bool SMOSimulator::step()
{
  return handleEvent();
}


void SMOSimulator::printCurrentState() const
{
  std::cout << "\n=== ТЕКУЩЕЕ СОСТОЯНИЕ СИСТЕМЫ ===\n";
  std::cout << "Время: " << currentTime << "\n";

  std::cout << "\nРестораны:\n";
  for (auto& r : restaurants)
    std::cout << "  Ресторан " << r.getRestaurantId()
    << " сгенерировал: " << r.getGeneratedCount()
    << " next=" << r.getNextGenerationTime() << "\n";

  std::cout << "\nБуфер: " << buffer.getSize()
    << "/" << buffer.getCapacity() << "\n";

  for (int i = 0; i < buffer.getCapacity(); i++)
  {
    auto& slot = buffer.getOrders()[i];
    if (slot.has_value())
    {
      std::cout << "  [" << i << "] "
        << slot->toString() << "\n";
    }
    else
    {
      std::cout << "  [" << i << "] EMPTY\n";
    }
  }

  std::cout << "\nОператоры:\n";
  for (auto& op : operators)
  {
    std::cout << "  Оператор " << op.getOperatorId() << ": ";
    if (op.isBusy())
    {
      auto ord = op.getCurrentOrder();
      std::cout << "занят (" << ord.first << "," << ord.second
        << ") finish=" << op.getCompletionTime();
    }
    else
    {
      std::cout << "свободен";
    }
    std::cout << "\n";
  }
}


void SMOSimulator::printEventCalendar() const
{
  std::cout << "\n=== КАЛЕНДАРЬ СОБЫТИЙ ===\n";

  auto copy = eventCalendar;
  while (!copy.empty())
  {
    const Event& e = copy.top();
    std::cout << "t=" << e.time << " : " << e.toString() << "\n";
    copy.pop();
  }
}


double SMOSimulator::getCurrentTime() const
{
  return currentTime;
}

int SMOSimulator::getStepCount() const
{
  return stepCount;
}

const Statistics& SMOSimulator::getStatistics() const
{
  return statistics;
}
