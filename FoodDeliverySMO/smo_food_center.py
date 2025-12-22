import heapq
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, List


# ---------------------------
# События (EventSystem)
# ---------------------------
class EventType(Enum):
    ORDER_GENERATED = auto()      # ресторан сгенерировал заказ
    ORDER_TO_OPERATOR = auto()    # заказ назначен оператору (лог-событие)
    OPERATOR_FREE = auto()        # оператор завершил обработку
    ORDER_TO_BUFFER = auto()      # заказ положен в буфер (лог-событие)
    ORDER_REJECTED = auto()       # отказ (лог-событие)


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
        # чтобы календарь был читаемый, без "<EventType...>"
        return (
            f"Event(time={self.time:.4f}, type={self.etype.name}, "
            f"rest={self.restaurant_id}, order={self.order_id}, "
            f"op={self.operator_id}, buf_pos={self.buffer_pos}, "
            f"wait={self.wait_time:.4f})"
        )


# ---------------------------
# Заявка
# ---------------------------
@dataclass
class Order:
    restaurant_id: int
    order_id: int
    timestamp: float  # время поступления в систему

    def __str__(self):
        return f"Order{{restaurant={self.restaurant_id}, id={self.order_id}, time={self.timestamp:.2f}}}"


# ---------------------------
# Буфер (FIFO + сдвиг) — Д1032
# ---------------------------
class Buffer:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.orders: List[Order] = []

    def is_full(self) -> bool:
        return len(self.orders) >= self.capacity

    def is_empty(self) -> bool:
        return len(self.orders) == 0

    def add_fifo(self, order: Order) -> int:
        """
        Добавление в конец FIFO.
        Возвращает позицию, куда положили (для логов).
        """
        if self.is_full():
            return -1
        self.orders.append(order)
        return len(self.orders) - 1

    def pop_first(self) -> Optional[Order]:
        """Снять первый (FIFO)."""
        if self.is_empty():
            return None
        return self.orders.pop(0)

    def pop_first_by_restaurant(self, restaurant_id: int) -> Optional[Order]:
        """
        Для Д2Б5: взять из буфера первый заказ заданного ресторана,
        сохраняя общий FIFO порядок внутри ресторана (по появлению в очереди).
        """
        for i, o in enumerate(self.orders):
            if o.restaurant_id == restaurant_id:
                return self.orders.pop(i)  # сдвиг сохраняется автоматически
        return None

    def restaurants_present(self) -> List[int]:
        """Список уникальных restaurant_id, которые есть в буфере."""
        return sorted({o.restaurant_id for o in self.orders})

    def __str__(self):
        if not self.orders:
            return "(пусто)"
        return "\n".join(f"  [{i}] {o}" for i, o in enumerate(self.orders))


# ---------------------------
# Источник заявок (ИБ + И31)
# ---------------------------
class RestaurantSource:
    """
    ИБ + И31: бесконечный источник, межприход равномерный (Uniform).
    Чтобы среднее межприхода было interval_mean, используем Uniform(0, 2*interval_mean).
    """

    def __init__(self, restaurant_id: int, interval_mean: float):
        self.restaurant_id = restaurant_id
        self.interval_mean = interval_mean
        self.generated = 0

        # первый заказ: тоже по равномерному закону, но не ровно в 0
        dt0 = random.uniform(0.0, 2.0 * self.interval_mean)
        if dt0 <= 1e-9:
            dt0 = 1e-6
        self.next_time = dt0

    def _next_dt(self) -> float:
        dt = random.uniform(0.0, 2.0 * self.interval_mean)
        if dt <= 1e-9:
            dt = 1e-6
        return dt

    def generate_event(self) -> Event:
        ev = Event(
            time=self.next_time,
            etype=EventType.ORDER_GENERATED,
            restaurant_id=self.restaurant_id,
            order_id=self.generated
        )
        self.generated += 1
        self.next_time += self._next_dt()
        return ev


# ---------------------------
# Оператор (П32: экспоненциальное время обслуживания)
# ---------------------------
class Operator:
    def __init__(self, operator_id: int, mean_service_time: float):
        self.operator_id = operator_id
        self.mean_service_time = mean_service_time  # <-- время обработки (среднее)
        self.busy = False
        self.current_order: Optional[Order] = None

        # для Д2Б5: текущий "пакет" ресторана
        self.batch_restaurant_id: Optional[int] = None

    def start_service(self, order: Order, current_time: float) -> Event:
        self.busy = True
        self.current_order = order

        # Д2Б5: оператор ведёт пакет ресторана, который сейчас обслуживает
        self.batch_restaurant_id = order.restaurant_id

        # П32: экспоненциальное время обслуживания
        dt = random.expovariate(1.0 / self.mean_service_time)
        finish_time = current_time + dt

        wait_time = current_time - order.timestamp  # ожидание до начала обслуживания

        return Event(
            time=finish_time,
            etype=EventType.OPERATOR_FREE,
            restaurant_id=order.restaurant_id,
            order_id=order.order_id,
            operator_id=self.operator_id,
            wait_time=wait_time
        )

    def free(self):
        self.busy = False
        self.current_order = None
        # batch_restaurant_id НЕ сбрасываем сразу:
        # по Д2Б5 при освобождении оператор пытается продолжать пакет
        # (если в буфере остались заказы этого ресторана)


# ---------------------------
# СМО: диспетчер постановки + выбор + календарь событий
# ---------------------------
class SMO:
    def __init__(
        self,
        num_restaurants: int = 3,
        num_operators: int = 2,
        interval_mean: float = 5.0,     # И31: средний межприход
        op_mean: float = 5.0,           # П32: среднее время обслуживания
        buffer_cap: int = 5,
        seed: Optional[int] = None
    ):
        if seed is not None:
            random.seed(seed)

        self.time = 0.0
        self.buffer = Buffer(buffer_cap)
        self.operators = [Operator(i, op_mean) for i in range(num_operators)]
        self.restaurants = [RestaurantSource(i, interval_mean) for i in range(num_restaurants)]

        # очередь событий (EventSystem)
        self.event_queue: List[Event] = []
        self.last_events: List[Event] = []  # календарь (лог)

        # статистика
        self.total_generated = 0
        self.total_processed = 0
        self.total_rejected = 0
        self.wait_times = [[] for _ in range(num_restaurants)]

        # начальные события генерации
        for r in self.restaurants:
            heapq.heappush(self.event_queue, r.generate_event())

    # ---- helpers (Д2П1) ----
    def _get_free_operator_d2p1(self) -> Optional[Operator]:
        free_ops = [op for op in self.operators if not op.busy]
        if not free_ops:
            return None
        return min(free_ops, key=lambda o: o.operator_id)  # Д2П1

    # ---- helpers (Д2Б5) ----
    def _select_restaurant_for_batch(self) -> Optional[int]:
        """
        По Д2Б5: выбираем ресторан по номеру источника (минимальный id),
        среди тех, чьи заказы есть в буфере.
        """
        rests = self.buffer.restaurants_present()
        return rests[0] if rests else None

    def _take_order_from_buffer_d2b5(self, op: Operator) -> Optional[Order]:
        """
        Д2Б5: если у оператора есть активный ресторан пакета и в буфере
        остались его заказы — берём их. Иначе выбираем новый ресторан (min id).
        """
        if self.buffer.is_empty():
            return None

        # 1) попытка продолжить текущий пакет
        if op.batch_restaurant_id is not None:
            order = self.buffer.pop_first_by_restaurant(op.batch_restaurant_id)
            if order is not None:
                return order

        # 2) если пакет закончился — выбираем новый ресторан (min id)
        new_rest = self._select_restaurant_for_batch()
        if new_rest is None:
            return None

        op.batch_restaurant_id = new_rest
        return self.buffer.pop_first_by_restaurant(new_rest)

    # ---- Event queue ----
    def push_event(self, ev: Event):
        heapq.heappush(self.event_queue, ev)

    def _log(self, ev: Event):
        self.last_events.append(ev)

    # ---- step simulation ----
    def step(self) -> bool:
        if not self.event_queue:
            return False

        ev = heapq.heappop(self.event_queue)
        self.time = ev.time

        # всегда логируем то, что реально "происходит"
        self._log(ev)

        if ev.etype == EventType.ORDER_GENERATED:
            # 1) статистика генерации
            self.total_generated += 1

            # 2) запланировать следующее событие генерации этого ресторана
            rest = self.restaurants[ev.restaurant_id]
            self.push_event(rest.generate_event())

            # 3) диспетчер постановки (Д1032 + Д1005 + Д2П1)
            order = Order(ev.restaurant_id, ev.order_id, ev.time)
            op = self._get_free_operator_d2p1()

            if op is not None:
                # сразу на оператора
                self._log(Event(
                    time=self.time,
                    etype=EventType.ORDER_TO_OPERATOR,
                    restaurant_id=order.restaurant_id,
                    order_id=order.order_id,
                    operator_id=op.operator_id,
                    wait_time=0.0
                ))
                free_ev = op.start_service(order, self.time)
                self.push_event(free_ev)
            else:
                # операторов нет — попытка в буфер (FIFO)
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
                    # Д1005: отказ новой заявки без изменения буфера
                    self.total_rejected += 1
                    self._log(Event(
                        time=self.time,
                        etype=EventType.ORDER_REJECTED,
                        restaurant_id=order.restaurant_id,
                        order_id=order.order_id
                    ))

        elif ev.etype == EventType.OPERATOR_FREE:
            # оператор завершил обслуживание
            op = self.operators[ev.operator_id]
            op.free()

            self.total_processed += 1
            self.wait_times[ev.restaurant_id].append(ev.wait_time)

            # диспетчер выбора (Д2Б5) + выбор оператора (оп уже известен, он освободился)
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
                free_ev = op.start_service(order, self.time)
                self.push_event(free_ev)
            else:
                # буфер пуст — пакет "зависает" (или можно сбросить)
                # по диаграмме это нормально: оператор просто свободен
                pass

        return True

    # ---- printing ----
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
                print(f"  Оператор {op.operator_id}: занят ({o.restaurant_id},{o.order_id}), batch={op.batch_restaurant_id}")
            else:
                print(f"  Оператор {op.operator_id}: свободен, batch={op.batch_restaurant_id}")

    def print_statistics(self):
        print("\n" + "=" * 70)
        print("СТАТИСТИКА СИСТЕМЫ")
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

    def print_calendar(self, last_n: int = 80):
        print("\n=== Последние события ===")
        tail = self.last_events[-last_n:] if last_n > 0 else self.last_events
        for ev in tail:
            print(ev)


# ---------------------------
# CLI
# ---------------------------
def main():
    print("=== СИМУЛЯЦИЯ СМО - ЦЕНТР ОБРАБОТКИ ЗАКАЗОВ ДОСТАВКИ ЕДЫ ===")

    # можешь тут менять параметры:
    # interval_mean — средний межприход (I31)
    # op_mean — среднее время обслуживания (P32)
    smo = SMO(
        num_restaurants=3,
        num_operators=2,
        interval_mean=5.0,
        op_mean=5.0,
        buffer_cap=5,
        seed=None  # поставь число для повторяемости
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
            smo.print_statistics()

        elif cmd == "2":
            t_max = float(input("До какого времени моделировать? "))
            while smo.time < t_max and smo.step():
                pass
            print("\nАвтоматическая симуляция завершена.")
            smo.print_statistics()

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
