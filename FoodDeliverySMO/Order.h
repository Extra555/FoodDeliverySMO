#ifndef ORDER_H
#define ORDER_H

#include <string>

class Order {
private:
  int restaurantId;
  int orderId;
  double timestamp;
  std::string details;

public:
  Order(int restId, int ordId, double time, const std::string& det = "");

  
  int getRestaurantId() const;
  int getOrderId() const;
  double getTimestamp() const;
  std::string getDetails() const;
  std::string toString() const;
};

#endif
