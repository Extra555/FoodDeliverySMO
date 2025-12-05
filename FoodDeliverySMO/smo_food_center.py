import heapq
import random
from dataclasses import dataclass
from enum import Enum, auto


# ============================================================
#                     EVENT STRUCTURES
# ============================================================

class EventType(Enum):
    ORDER_GENERATED = auto()
    ORDER_TO_OPERATOR = auto()
    OPERATOR_FREE = auto()
    ORDER_TO_BUFFER = auto()
    ORDER_REJECTED = auto()


@dataclass(order=True)
class Event:
    time: float
    etype: EventType
    restaurant_id: int = -1
    order_id: int = -1
    operator_id: int = -1
    buffer_pos: int = -1
    wait_time: float = 0.0


# ============================================================
#                       ORDER OBJECT
# ============================================================

@dataclass
class Order:
    restaurant_id: int
    order_id: int
    timestamp: float

    def __str__(self):
        return f"Order{{restaurant={self.restaurant_id}, id={self.order_id}, time={self.timestamp:.2f}}}"


# ============================================================
#                       BUFFER (FIFO + shift)
# ============================================================

class Buffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.orders = []

    def is_full(self):
        return len(self.orders) >= self.capacity

    def is_empty(self):
        return len(self.orders) == 0

    def add(self, order: Order):
        if self.is_full():
            return False
        self.orders.append(order)
        return True

    def pop_first(self):
        if self.is_empty():
            return None
        return self.orders.pop(0)

    def __str__(self):
        if not self.orders:
            return "(пусто)"
        return "\n".join(
            f"  [{i}] {o}" for i, o in enumerate(self.orders)
        )


# ============================================================
#                     RESTAURANT SOURCE
# ============================================================

class RestaurantSource:
    """
    Генерация заказов НЕ начинается в момент 0.
    Первый заказ появляется в момент interval.
    """

    def __init__(self, restaurant_id: int, interval: float):
        self.restaurant_id = restaurant_id
        self.interval = interval
        self.generated = 0
        self.next_time = interval  # <-- ключевая правка

    def generate_event(self):
        """Создаёт заказ в момент next_time"""
        ev = Event(
            time=self.next_time,
            etype=EventType.ORDER_GENERATED,
            restaurant_id=self.restaurant_id,
            order_id=self.generated
        )
        self.generated += 1
        self.next_time += self.interval
        return ev


# ============================================================
#                     OPERATOR OBJECT
# ============================================================

class Operator:
    def __init__(self, operator_id: int, mean_service_time: float):
        self.operator_id = operator_id
        self.mean_service_time = mean_service_time
        self.busy = False
        self.current_order = None

    def start_service(self, order: Order, current_time: float):
        self.busy = True
        self.current_order = order

        # экспоненциальное время обработки
        dt = random.expovariate(1.0 / self.mean_service_time)
        finish_time = current_time + dt

        return Event(
            time=finish_time,
            etype=EventType.OPERATOR_FREE,
            restaurant_id=order.restaurant_id,
            order_id=order.order_id,
            operator_id=self.operator_id,
            wait_time=current_time - order.timestamp
        )

    def free(self):
        self.busy = False
        self.current_order = None


# ============================================================
#                        SIMULATOR
# ============================================================

class SMO:
    def __init__(self, num_restaurants=3, num_operators=2,
                 interval=5.0, op_mean=5.0, buffer_cap=5):  #oper time (op_mean)  PARAMS

        self.time = 0.0
        self.buffer = Buffer(buffer_cap)
        self.operators = [Operator(i, op_mean) for i in range(num_operators)]
        self.restaurants = [
            RestaurantSource(i, interval) for i in range(num_restaurants)
        ]

        self.event_queue = []
        self.last_events = []

        # статистика
        self.total_generated = 0
        self.total_processed = 0
        self.total_rejected = 0
        self.wait_times = [[] for _ in range(num_restaurants)]

        # начальные события
        for r in self.restaurants:
            heapq.heappush(self.event_queue, r.generate_event())

    def push_event(self, ev):
        heapq.heappush(self.event_queue, ev)

    def step(self):
        if not self.event_queue:
            return False

        ev = heapq.heappop(self.event_queue)
        self.time = ev.time
        self.last_events.append(ev)

        if ev.etype == EventType.ORDER_GENERATED:
            self.total_generated += 1
            rest = self.restaurants[ev.restaurant_id]
            next_ev = rest.generate_event()
            self.push_event(next_ev)

            # give order to free operator?
            order = Order(ev.restaurant_id, ev.order_id, ev.time)
            op = next((o for o in self.operators if not o.busy), None)

            if op is not None:
                free_ev = op.start_service(order, self.time)
                self.push_event(free_ev)
            else:
                if not self.buffer.add(order):
                    self.total_rejected += 1

        elif ev.etype == EventType.OPERATOR_FREE:
            op = self.operators[ev.operator_id]
            op.free()
            self.total_processed += 1
            self.wait_times[ev.restaurant_id].append(ev.wait_time)

            if not self.buffer.is_empty():
                order = self.buffer.pop_first()
                free_ev = op.start_service(order, self.time)
                self.push_event(free_ev)

        return True

    # ----------------------------------------------------------
    # PRINTING
    # ----------------------------------------------------------

    def print_state(self):
        print("\n=== ТЕКУЩЕЕ СОСТОЯНИЕ ===")
        print(f"Время: {self.time:.2f}")

        print("\nРестораны:")
        for r in self.restaurants:
            print(f"  Ресторан {r.restaurant_id}: next={r.next_time:.2f}, generated={r.generated}")

        print(f"\nБуфер: {len(self.buffer.orders)}/{self.buffer.capacity}")
        print(self.buffer)

        print("\nОператоры:")
        for op in self.operators:
            if op.busy:
                o = op.current_order
                print(f"  Оператор {op.operator_id}: занят ({o.restaurant_id},{o.order_id})")
            else:
                print(f"  Оператор {op.operator_id}: свободен")

    def print_statistics(self):
        print("\n" + "=" * 70)
        print("СТАТИСТИКА СИСТЕМЫ")
        print("=" * 70)

        print(f"Всего заказов: {self.total_generated}")
        print(f"Обработано:   {self.total_processed}")
        print(f"Отклонено:    {self.total_rejected}")
        if self.total_generated > 0:
            print(f"Процент отказа: {(self.total_rejected/self.total_generated)*100:.2f}%")

        print("\nПо ресторанам:")
        for i, waits in enumerate(self.wait_times):
            avg_wait = sum(waits)/len(waits) if waits else 0
            print(f"  Ресторан {i}: обработано={len(waits)}, ср. ожидание={avg_wait:.2f}")

    def print_calendar(self):
        print("\n=== Последние события ===")
        for ev in self.last_events:
            print(ev)


# ============================================================
#                 USER INTERFACE (MENU)
# ============================================================

def main():
    print("=== СИМУЛЯЦИЯ СМО - ЦЕНТР ОБРАБОТКИ ЗАКАЗОВ ДОСТАВКИ ЕДЫ ===")

    smo = SMO()

    while True:
        print("\n1. Пошаговый режим")
        print("2. Автоматический режим")
        print("3. Показать календарь событий")
        print("4. Выход")
        cmd = input("Выберите опцию: ")

        if cmd == "1":
            t_max = float(input("Введите время симуляции: "))
            print("Симуляция начата. Enter — следующий шаг, q — выход.")
            while smo.time < t_max and smo.step():
                print("\n" + "=" * 60)
                print(f"ШАГ — время {smo.time:.2f}")
                smo.print_state()
                if input() == "q":
                    break
            smo.print_statistics()

        elif cmd == "2":
            t_max = float(input("До какого времени моделировать? "))
            while smo.time < t_max and smo.step():
                pass
            print("\nАвтоматическая симуляция завершена.")
            smo.print_statistics()

        elif cmd == "3":
            smo.print_calendar()

        elif cmd == "4":
            print("Выход.")
            break


if __name__ == "__main__":
    main()
