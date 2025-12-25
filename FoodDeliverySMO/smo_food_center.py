import heapq
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List


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

    def __str__(self) -> str:
        return (
            f"Event(time={self.time:.4f}, type={self.etype.name}, "
            f"rest={self.restaurant_id}, order={self.order_id}, "
            f"op={self.operator_id}, buf_pos={self.buffer_pos}, "
            f"wait={self.wait_time:.4f})"
        )


@dataclass
class Order:
    restaurant_id: int
    order_id: int
    timestamp: float

    def __str__(self):
        return f"Order{{restaurant={self.restaurant_id}, id={self.order_id}, time={self.timestamp:.2f}}}"


class Buffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.orders: List[Order] = []

    def is_full(self) -> bool:
        return len(self.orders) >= self.capacity

    def is_empty(self) -> bool:
        return len(self.orders) == 0

    def add_fifo(self, order: Order) -> int:
        if self.is_full():
            return -1
        self.orders.append(order)
        return len(self.orders) - 1

    def pop_first(self) -> Optional[Order]:
        if self.is_empty():
            return None
        return self.orders.pop(0)

    def pop_first_by_restaurant(self, restaurant_id: int) -> Optional[Order]:
        for i, o in enumerate(self.orders):
            if o.restaurant_id == restaurant_id:
                return self.orders.pop(i)
        return None

    def restaurants_present(self) -> List[int]:
        return sorted({o.restaurant_id for o in self.orders})

    def __str__(self):
        if not self.orders:
            return "(пусто)"
        return "\n".join(f"  [{i}] {o}" for i, o in enumerate(self.orders))


class RestaurantSource:
    def __init__(self, restaurant_id: int, interval: float, start_offset: float = 0.0):
        self.restaurant_id = restaurant_id
        self.interval = interval
        self.generated = 0
        self.next_time = start_offset

    def generate_event(self) -> Event:
        ev = Event(
            time=self.next_time,
            etype=EventType.ORDER_GENERATED,
            restaurant_id=self.restaurant_id,
            order_id=self.generated
        )
        self.generated += 1
        self.next_time += self.interval
        return ev


class Operator:
    def __init__(self, operator_id: int, mean_service_time: float):
        self.operator_id = operator_id
        self.mean_service_time = mean_service_time
        self.busy = False
        self.current_order: Optional[Order] = None
        self.batch_restaurant_id: Optional[int] = None

        # --- для расширенной статистики ---
        self.busy_time = 0.0
        self.last_start_time: Optional[float] = None

    def start_service(self, order: Order, current_time: float) -> Event:
        self.busy = True
        self.current_order = order
        self.batch_restaurant_id = order.restaurant_id

        # для загрузки прибора
        self.last_start_time = current_time

        dt = random.expovariate(1.0 / self.mean_service_time)  # П32
        finish_time = current_time + dt
        wait_time = current_time - order.timestamp
        return Event(
            time=finish_time,
            etype=EventType.OPERATOR_FREE,
            restaurant_id=order.restaurant_id,
            order_id=order.order_id,
            operator_id=self.operator_id,
            wait_time=wait_time
        )

    def free(self, current_time: float):
        # для загрузки прибора
        if self.last_start_time is not None:
            self.busy_time += (current_time - self.last_start_time)
        self.busy = False
        self.current_order = None
        self.last_start_time = None


class SMO:
    def __init__(
        self,
        num_restaurants: int = 15,
        num_operators: int = 50,
        interval: float = 0.2,   # средний интервал (интенсивность ~ 1/interval)
        op_mean: float = 2.0,
        buffer_cap: int = 100,
        seed: Optional[int] = 1
    ):
        if seed is not None:
            random.seed(seed)

        self.time = 0.0
        self.buffer = Buffer(buffer_cap)
        self.operators = [Operator(i, op_mean) for i in range(num_operators)]

        self.restaurants: List[RestaurantSource] = []
        for i in range(num_restaurants):
            start_offset = (i * interval) / num_restaurants
            self.restaurants.append(RestaurantSource(i, interval, start_offset))

        self.event_queue: List[Event] = []
        self.last_events: List[Event] = []

        # --- старая статистика ---
        self.total_generated = 0
        self.total_processed = 0
        self.total_rejected = 0
        self.wait_times = [[] for _ in range(num_restaurants)]

        # --- новая статистика (дополнительно) ---
        self.rejected_by_restaurant = [0] * num_restaurants
        self.system_times = [[] for _ in range(num_restaurants)]  # T пребывания в системе

        # средняя длина буфера (интеграл длины)
        self.buffer_area = 0.0
        self.last_event_time = 0.0

        for r in self.restaurants:
            heapq.heappush(self.event_queue, r.generate_event())

    def _get_free_operator_d2p1(self) -> Optional[Operator]:
        free_ops = [op for op in self.operators if not op.busy]
        if not free_ops:
            return None
        return min(free_ops, key=lambda o: o.operator_id)

    def _select_restaurant_for_batch(self) -> Optional[int]:
        rests = self.buffer.restaurants_present()
        return rests[0] if rests else None

    def _take_order_from_buffer_d2b5(self, op: Operator) -> Optional[Order]:
        if self.buffer.is_empty():
            return None
        if op.batch_restaurant_id is not None:
            order = self.buffer.pop_first_by_restaurant(op.batch_restaurant_id)
            if order is not None:
                return order
        new_rest = self._select_restaurant_for_batch()
        if new_rest is None:
            return None
        op.batch_restaurant_id = new_rest
        return self.buffer.pop_first_by_restaurant(new_rest)

    def push_event(self, ev: Event):
        heapq.heappush(self.event_queue, ev)

    def _log(self, ev: Event):
        self.last_events.append(ev)

    def step(self) -> bool:
        if not self.event_queue:
            return False

        ev = heapq.heappop(self.event_queue)

        # --- средняя длина буфера: накапливаем площадь len(buffer)*dt ---
        dt = ev.time - self.last_event_time
        if dt > 0:
            self.buffer_area += len(self.buffer.orders) * dt
            self.last_event_time = ev.time

        self.time = ev.time
        self._log(ev)

        if ev.etype == EventType.ORDER_GENERATED:
            self.total_generated += 1
            rest = self.restaurants[ev.restaurant_id]
            self.push_event(rest.generate_event())

            order = Order(ev.restaurant_id, ev.order_id, ev.time)
            op = self._get_free_operator_d2p1()

            if op is not None:
                self._log(Event(
                    time=self.time,
                    etype=EventType.ORDER_TO_OPERATOR,
                    restaurant_id=order.restaurant_id,
                    order_id=order.order_id,
                    operator_id=op.operator_id,
                    wait_time=0.0
                ))
                self.push_event(op.start_service(order, self.time))
            else:
                if not self.buffer.is_full():
                    pos = self.buffer.add_fifo(order)
                    self._log(Event(
                        time=self.time,
                        etype=EventType.ORDER_TO_BUFFER,
                        restaurant_id=order.restaurant_id,
                        order_id=order.order_id,
                        buffer_pos=pos
                    ))
                else:
                    self.total_rejected += 1
                    self.rejected_by_restaurant[order.restaurant_id] += 1
                    self._log(Event(
                        time=self.time,
                        etype=EventType.ORDER_REJECTED,
                        restaurant_id=order.restaurant_id,
                        order_id=order.order_id
                    ))

        elif ev.etype == EventType.OPERATOR_FREE:
            op = self.operators[ev.operator_id]

            # --- корректное T пребывания: берём timestamp у текущей заявки прибора ---
            finished_order = op.current_order
            if finished_order is not None:
                system_time = self.time - finished_order.timestamp
                self.system_times[finished_order.restaurant_id].append(system_time)

            op.free(self.time)

            self.total_processed += 1
            self.wait_times[ev.restaurant_id].append(ev.wait_time)

            order = self._take_order_from_buffer_d2b5(op)
            if order is not None:
                self._log(Event(
                    time=self.time,
                    etype=EventType.ORDER_TO_OPERATOR,
                    restaurant_id=order.restaurant_id,
                    order_id=order.order_id,
                    operator_id=op.operator_id,
                    wait_time=self.time - order.timestamp
                ))
                self.push_event(op.start_service(order, self.time))

        return True

    def print_state(self):
        print("\n=== ТЕКУЩЕЕ СОСТОЯНИЕ ===")
        print(f"Время: {self.time:.2f}")

        print("\nРестораны (ИБ + ИЗ1):")
        for r in self.restaurants:
            print(f"  Ресторан {r.restaurant_id}: interval={r.interval:.2f}, next={r.next_time:.2f}, generated={r.generated}")

        print(f"\nБуфер (Д1ОЗ2): {len(self.buffer.orders)}/{self.buffer.capacity}")
        print(self.buffer)

        print("\nОператоры (П32):")
        for op in self.operators:
            if op.busy:
                o = op.current_order
                print(f"  Оператор {op.operator_id}: занят ({o.restaurant_id},{o.order_id}), batch={op.batch_restaurant_id}")
            else:
                print(f"  Оператор {op.operator_id}: свободен, batch={op.batch_restaurant_id}")


    def print_statistics(self):
        print("\n" + "=" * 70)
        print("СТАТИСТИКА СИСТЕМЫ (ОР1)")
        print("=" * 70)

        print(f"Всего заказов (сгенерировано): {self.total_generated}")
        print(f"Обработано:                 {self.total_processed}")
        print(f"Отклонено:                  {self.total_rejected}")
        if self.total_generated > 0:
            print(f"Процент отказа:             {(self.total_rejected / self.total_generated) * 100:.2f}%")

        print("\nПо ресторанам:")
        for i, waits in enumerate(self.wait_times):
            avg_wait = sum(waits) / len(waits) if waits else 0.0
            print(f"  Ресторан {i}: обработано={len(waits)}, ср. ожидание={avg_wait:.2f}")


    def print_extended_statistics(self):
        print("\n" + "=" * 70)
        print("РАСШИРЕННАЯ СТАТИСТИКА")
        print("=" * 70)

        def mean(xs: List[float]) -> float:
            return sum(xs) / len(xs) if xs else 0.0

        def var(xs: List[float]) -> float:
            if not xs:
                return 0.0
            m = mean(xs)
            return (sum(x * x for x in xs) / len(xs)) - (m * m)

        print("\nПо источникам (ресторанам):")
        for i, src in enumerate(self.restaurants):
            gen_i = src.generated
            rej_i = self.rejected_by_restaurant[i]
            p_rej = (rej_i / gen_i) if gen_i > 0 else 0.0

            w = self.wait_times[i]
            t = self.system_times[i]

            print(
                f"  Источник {i}: "
                f"заявок={gen_i}, "
                f"отказов={rej_i}, "
                f"Pотк={p_rej:.3f}, "
                f"E[Tож]={mean(w):.2f}, D[Tож]={var(w):.2f}, "
                f"E[Tпр]={mean(t):.2f}, D[Tпр]={var(t):.2f}"
            )

        print("\nЗагрузка приборов (Kисп и процент загрузки):")
        T = self.time if self.time > 0 else 1.01
        for op in self.operators:
            k = op.busy_time / T
            percent = k * 100
            print(
                f"  Прибор {op.operator_id}: "
                f"Kисп={k:.3f}, "
                f"загрузка={percent:.1f}%"
            )

        avg_buf = (self.buffer_area / T) if T > 0 else 0.0
        print(f"\nСредняя длина буфера: {avg_buf:.2f}")

    def print_calendar(self, last_n: int = 80):
        print("\n=== Последние события (ОД3) ===")
        tail = self.last_events[-last_n:] if last_n > 0 else self.last_events
        for ev in tail:
            print(ev)


def main():
    print("=== СИМУЛЯЦИЯ СМО - ЦЕНТР ОБРАБОТКИ ЗАКАЗОВ ДОСТАВКИ ЕДЫ ===")

    smo = SMO(
        num_restaurants=15,
        num_operators=5,
        interval=10.0,
        op_mean=2.0,
        buffer_cap=3,
        seed=1
    )

    while True:
        print("\n1. Пошаговый режим")
        print("2. Автоматический режим")
        print("3. Показать календарь событий")
        print("4. Выход")
        cmd = input("Выберите опцию: ").strip()

        if cmd == "1":
            t_max = float(input("Введите время симуляции: "))
            print("Симуляция начата. Enter — следующий шаг, q — выход.")
            while smo.time < t_max and smo.step():
                print("\n" + "=" * 60)
                print(f"ШАГ — время {smo.time:.2f}")
                smo.print_state()
                if input().strip().lower() == "q":
                    break
            smo.print_statistics()  # только старая статистика

        elif cmd == "2":
            t_max = float(input("До какого времени моделировать? "))
            while smo.time < t_max and smo.step():
                pass
            print("\nАвтоматическая симуляция завершена.")
            smo.print_statistics()            # старая статистика
            smo.print_extended_statistics()   # новая расширенная

        elif cmd == "3":
            try:
                n = input("Сколько последних событий вывести? (Enter=80): ").strip()
                n = int(n) if n else 80
            except ValueError:
                n = 80
            smo.print_calendar(last_n=n)

        elif cmd == "4":
            print("Выход.")
            break


if __name__ == "__main__":
    main()
