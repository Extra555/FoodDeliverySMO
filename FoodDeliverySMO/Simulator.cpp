#define _CRT_SECURE_NO_WARNINGS
#include "Simulator.h"
#include <iostream>
#include <iomanip>
#include <limits>

SMOSimulator::SMOSimulator(int numRest, int numOp, int bufCap, double genInt, double procMean)
  : numRestaurants(numRest), numOperators(numOp), bufferCapacity(bufCap),
  generationInterval(genInt), processingTimeMean(procMean),
  buffer(bufCap), statistics(numRest),
  placementDispatcher(buffer, statistics), selectionDispatcher(buffer),
  currentTime(0), stepCount(0) {

  for (int i = 0; i < numRestaurants; i++) {
    restaurants.emplace_back(i, generationInterval);
  }

  for (int i = 0; i < numOperators; i++) {
    operators.emplace_back(i, processingTimeMean);
  }
}

void SMOSimulator::initializeSimulation(double simulationTime) {
  currentTime = 0;
  stepCount = 0;

  while (!eventCalendar.empty()) {
    eventCalendar.pop();
  }
  stepEvents.clear();

  for (auto& restaurant : restaurants) {
    restaurant.reset();
  }
  buffer.clear();
  for (auto& op : operators) {
    op.reset();
  }
  statistics.reset();
  selectionDispatcher.reset();

  
  for (auto& restaurant : restaurants) {
    Event event = restaurant.generateOrder(0);
    eventCalendar.push({ event.time, event });
  }
}

bool SMOSimulator::step() {
  if (eventCalendar.empty()) {
    std::cout << "=== КАЛЕНДАРЬ СОБЫТИЙ ПУСТ ===" << std::endl;
    return false;
  }

  auto [eventTime, event] = eventCalendar.top();
  eventCalendar.pop();

  
  if (eventTime > currentTime) {
    currentTime = eventTime;
  }
  stepCount++;

  
  std::cout << "\n=== ОБРАБОТКА СОБЫТИЯ ===" << std::endl;
  std::cout << "Шаг: " << stepCount << std::endl;
  std::cout << "Время события: " << eventTime << std::endl;
  std::cout << "Текущее время системы: " << currentTime << std::endl;
  std::cout << "Событие: " << event.toString() << std::endl;

  stepEvents.clear();
  std::vector<Event> newEvents = processEvent(event);
  stepEvents.push_back(event);

  
  for (const auto& newEvent : newEvents) {
    std::cout << "Добавлено новое событие: " << newEvent.toString() << std::endl;
    eventCalendar.push({ newEvent.time, newEvent });
    stepEvents.push_back(newEvent);
  }

  return true;
}

void SMOSimulator::printCurrentState() const {
  std::cout << "\n=== ТЕКУЩЕЕ СОСТОЯНИЕ СИСТЕМЫ (шаг " << stepCount << ", время " << currentTime << ") ===\n";

  std::cout << "РЕСТОРАНЫ:\n";
  for (const auto& restaurant : restaurants) {
    std::cout << "  Ресторан " << restaurant.getRestaurantId() << ": сгенерировано=" << restaurant.getGeneratedCount()
      << ", след.генерация=" << restaurant.getNextGenerationTime() << "\n";
  }

  std::cout << "БУФЕР ЗАКАЗОВ (размер=" << buffer.getSize() << "/" << buffer.getCapacity() << "):\n";
  for (int i = 0; i < buffer.getCapacity(); i++) {
    if (buffer.getOrders()[i].has_value()) {
      const auto& order = buffer.getOrders()[i].value();
      std::cout << "  Позиция " << i << ": ресторан=" << order.getRestaurantId()
        << ", заказ=" << order.getOrderId()
        << ", время поступления=" << order.getTimestamp() << "\n";
    }
    else {
      std::cout << "  Позиция " << i << ": свободно\n";
    }
  }

  std::cout << "ОПЕРАТОРЫ:\n";
  for (const auto& op : operators) {
    std::cout << "  Оператор " << op.getOperatorId() << ": ";
    if (op.isBusy()) {
      std::cout << "занят, заказ (ресторан=" << op.getCurrentOrder().first
        << ", id=" << op.getCurrentOrder().second
        << ", завершение=" << op.getCompletionTime() << ")";
    }
    else {
      std::cout << "свободен";
    }
    std::cout << ", обработано=" << op.getProcessedCount() << "\n";
  }

  auto packageInfo = selectionDispatcher.getCurrentPackageInfo();
  std::cout << "ТЕКУЩИЙ ПАКЕТ: ресторан=" << packageInfo.first
    << ", размер=" << packageInfo.second << "\n";

  std::cout << "СТАТИСТИКА: всего=" << statistics.getTotalOrders()
    << ", обработано=" << statistics.getTotalProcessed()
    << ", отказано=" << statistics.getTotalRejected()
    << " (" << std::fixed << std::setprecision(2) << (statistics.getRejectionRate() * 100) << "%)\n";
}

void SMOSimulator::printEventCalendar() const {
  std::cout << "\nКАЛЕНДАРЬ СОБЫТИЙ:\n";

  auto calendarCopy = eventCalendar;
  std::vector<std::pair<double, Event>> events;

  while (!calendarCopy.empty()) {
    events.push_back(calendarCopy.top());
    calendarCopy.pop();
  }

  for (const auto& [time, event] : events) {
    std::cout << "  Время " << time << ": " << event.toString() << "\n";
  }
}

std::vector<Event> SMOSimulator::processEvent(const Event& event) {
  switch (event.type) {
  case EventType::ORDER_GENERATED:
    return handleOrderGeneratedEvent(event);
  case EventType::ORDER_TO_BUFFER:
    return handleOrderToBufferEvent(event);
  case EventType::ORDER_TO_OPERATOR:
    return handleOrderToOperatorEvent(event);
  case EventType::ORDER_SELECTED:
    return handleOrderSelectedEvent(event);
  case EventType::OPERATOR_FREE:
    return handleOperatorFreeEvent(event);
  case EventType::DELIVERY_COORDINATION_START:
    return handleDeliveryCoordinationStartEvent(event);
  case EventType::ORDER_REJECTED:
    
    return {};
  default:
    return {};
  }
}

Operator* SMOSimulator::findFreeOperator() {
  
  for (int i = 0; i < operators.size(); i++) {
    if (!operators[i].isBusy()) {
      return &operators[i];
    }
  }
  return nullptr;
}

std::vector<Event> SMOSimulator::handleOrderGeneratedEvent(const Event& event) {
  std::vector<Event> newEvents;

  statistics.orderGenerated(event.restaurantId);

  auto placementEvents = placementDispatcher.handleNewOrder(restaurants, operators, event.time, event.restaurantId, event.orderId);
  newEvents.insert(newEvents.end(), placementEvents.begin(), placementEvents.end());

  
  Event nextGenEvent = restaurants[event.restaurantId].generateOrder(event.time);
  if (nextGenEvent.time > event.time) { 
    eventCalendar.push({ nextGenEvent.time, nextGenEvent });
  }

  return newEvents;
}

std::vector<Event> SMOSimulator::handleOrderToBufferEvent(const Event& event) {
  std::vector<Event> newEvents;

  
  Operator* freeOperator = findFreeOperator();
  if (freeOperator != nullptr) {
    auto selectionEvent = selectionDispatcher.selectNextOrder(operators, event.time);
    if (selectionEvent.has_value()) {
      newEvents.push_back(selectionEvent.value());
    }
  }

  return newEvents;
}

std::vector<Event> SMOSimulator::handleOrderToOperatorEvent(const Event& event) {
  std::vector<Event> newEvents;

  Operator* operatorPtr = &operators[event.operatorId];

  
  Event startEvent = operatorPtr->coordinateDelivery(event.restaurantId, event.orderId, event.time);

  
  Event completeEvent(EventType::OPERATOR_FREE, operatorPtr->getCompletionTime(),
    event.restaurantId, event.orderId, event.operatorId);
  eventCalendar.push({ completeEvent.time, completeEvent });

  
  statistics.orderProcessed(event.restaurantId, 0, operatorPtr->getCompletionTime() - event.time);

  return newEvents;
}

std::vector<Event> SMOSimulator::handleOrderSelectedEvent(const Event& event) {
  std::vector<Event> newEvents;

  
  auto order = buffer.removeOrder(event.bufferPosition);
  if (order.has_value()) {
    Operator* freeOperator = findFreeOperator();
    if (freeOperator != nullptr) {
      
      Event startEvent = freeOperator->coordinateDelivery(order->getRestaurantId(), order->getOrderId(), event.time);

      
      Event completeEvent(EventType::OPERATOR_FREE, freeOperator->getCompletionTime(),
        order->getRestaurantId(), order->getOrderId(), freeOperator->getOperatorId());
      eventCalendar.push({ completeEvent.time, completeEvent });

      
      statistics.orderProcessed(order->getRestaurantId(), event.waitTime,
        freeOperator->getCompletionTime() - event.time);
    }
  }

  return newEvents;
}

std::vector<Event> SMOSimulator::handleOperatorFreeEvent(const Event& event) {
  std::vector<Event> newEvents;

  
  operators[event.operatorId].completeProcessing(event.time);

  
  auto selectionEvent = selectionDispatcher.selectNextOrder(operators, event.time);
  if (selectionEvent.has_value()) {
    newEvents.push_back(selectionEvent.value());
  }

  return newEvents;
}

std::vector<Event> SMOSimulator::handleDeliveryCoordinationStartEvent(const Event& event) {
  
  return {};
}

double SMOSimulator::getCurrentTime() const { return currentTime; }
int SMOSimulator::getStepCount() const { return stepCount; }
const Statistics& SMOSimulator::getStatistics() const { return statistics; }
const Buffer& SMOSimulator::getBuffer() const { return buffer; }
const std::vector<Operator>& SMOSimulator::getOperators() const { return operators; }
const std::vector<RestaurantSource>& SMOSimulator::getRestaurants() const { return restaurants; }