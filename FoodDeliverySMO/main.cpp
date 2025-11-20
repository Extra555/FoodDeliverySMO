#define _CRT_SECURE_NO_WARNINGS
#include <iostream>
#include <iomanip>
#include <string>
#include <queue>
#include <vector>
#include <optional>
#include <random>
#include <limits>
#include <algorithm>
#include <set>
#include "Simulator.h"

void printMenu() {
  std::cout << "\n=== СИСТЕМА МАССОВОГО ОБСЛУЖИВАНИЯ ===\n";
  std::cout << "Вариант 9: Центр обработки заказов доставки еды\n";
  std::cout << "1. Пошаговый режим\n";
  std::cout << "2. Показать текущее состояние\n";
  std::cout << "3. Показать календарь событий\n";
  std::cout << "4. Сбросить симуляцию\n";
  std::cout << "5. Выход\n";
  std::cout << "Выберите опцию: ";
}

void printSystemInfo() {
  std::cout << "\n=== КОНФИГУРАЦИЯ СИСТЕМЫ ===\n";
  std::cout << "Рестораны: 3 ресторана с равномерным распределением\n";
  std::cout << "Операторы: 2 оператора с экспоненциальным временем обработки\n";
  std::cout << "Буфер заказов: 5 мест, дисциплина Д1ОЗ2 (сдвиг заказов)\n";
  std::cout << "Дисциплина отказа: Д1ОО5 (отказ нового заказа)\n";
  std::cout << "Дисциплина выбора заказов: Д2Б5 (пакетная обработка по ресторанам)\n";
}

void runStepMode(SMOSimulator& simulator) {
  std::cout << "\n=== ПОШАГОВЫЙ РЕЖИМ ===\n";

  double simulationTime;
  std::cout << "Введите время симуляции: ";
  std::cin >> simulationTime;

  simulator.initializeSimulation(simulationTime);

  std::cout << "Симуляция начата. Нажмите Enter для следующего шага, 'q' для выхода...\n";
  std::cin.ignore(); // Очистка буфера

  while (simulator.step()) {
    std::cout << "\n" << std::string(60, '=') << "\n";
    std::cout << "ШАГ " << simulator.getStepCount() << " - Время: " << simulator.getCurrentTime() << "\n";
    std::cout << std::string(60, '=') << "\n";

    simulator.printCurrentState();

    if (simulator.getCurrentTime() >= simulationTime) {
      std::cout << "\nДостигнуто время симуляции!\n";
      break;
    }

    std::cout << "\nНажмите Enter для продолжения...";
    std::string input;
    std::getline(std::cin, input);
    if (input == "q") {
      break;
    }
  }

  simulator.getStatistics().printSummary();
}

int main() {
  const int NUM_RESTAURANTS = 3;      
  const int NUM_OPERATORS = 2;        
  const int BUFFER_CAPACITY = 5;      
  const double GENERATION_INTERVAL = 5.0;    
  const double PROCESSING_TIME_MEAN = 3.0;   

  SMOSimulator simulator(NUM_RESTAURANTS, NUM_OPERATORS, BUFFER_CAPACITY,
    GENERATION_INTERVAL, PROCESSING_TIME_MEAN);

  
  setlocale(LC_ALL, "Russian");

  std::cout << "=== СИМУЛЯЦИЯ СМО - ЦЕНТР ОБРАБОТКИ ЗАКАЗОВ ДОСТАВКИ ЕДЫ ===\n";
  printSystemInfo();

  int choice;
  bool running = true;

  while (running) {
    printMenu();
    std::cin >> choice;
    std::cin.ignore(); 

    switch (choice) {
    case 1:
      runStepMode(simulator);
      break;

    case 2:
      if (simulator.getStepCount() > 0) {
        simulator.printCurrentState();
      }
      else {
        std::cout << "Симуляция еще не запущена!\n";
      }
      break;

    case 3:
      if (simulator.getStepCount() > 0) {
        simulator.printEventCalendar();
      }
      else {
        std::cout << "Симуляция еще не запущена!\n";
      }
      break;

    case 4:
      simulator.initializeSimulation(100.0); 
      std::cout << "Симуляция сброшена!\n";
      break;

    case 5:
      running = false;
      std::cout << "Выход из программы...\n";
      break;

    default:
      std::cout << "Неверный выбор! Попробуйте снова.\n";
      break;
    }
  }

  return 0;
}