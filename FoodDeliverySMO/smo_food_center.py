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

    def __str__(self) -> str:
        return f"Order{{restaurant={self.restaurant_id}, id={self.order_id}, time={self.timestamp:.2f}}}"


# ---------------------------
# Буфер (FIFO + сдвиг) — Д1ОЗ2
# ---------------------------
class Buffer:
    """
    Д1ОЗ2:
    - если приборы заняты, заявка занимает места буфера последовательно с первого,
      следующая в конец, пока есть свободные места;
    - при освобождении места N (вытаскивание/удаление) заявки с N+1.. сдвигаются влево.
    В Python list это естественно реализуется через insert/append + pop(i).
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.orders: List[Order] = []

    def is_full(self) -> bool:
        return len(self.orders) >= self.capacity

    def is_empty(self) -> bool:
        return len(self.orders) == 0

    def add_fifo(self, order: Order) -> int:
        """Положить в конец очереди, вернуть позицию (индекс) или -1 если полный."""
        if self.is_full():
            return -1
        self.orders.append(order)
        return len(self.orders) - 1

    def pop_first(self) -> Optional[Order]:
        """FIFO: снять первый."""
        if self.is_empty():
            return None
        return self.orders.pop(0)

    def pop_first_by_restaurant(self, restaurant_id: int) -> Optional[Order]:
        """
        Для Д2Б5: снять первую (по общему порядку в буфере) заявку заданного источника.
        pop(i) автоматически реализует "сдвиг" оставшихся.
        """
        for i, o in enumerate(self.orders):
            if o.restaurant_id == restaurant_id:
                return self.orders.pop(i)
        return None

    def restaurants_present(self) -> List[int]:
        """Какие источники (рестораны) сейчас представлены в буфере."""
        return sorted({o.restaurant_id for o in self.orders})

    def __str__(self) -> str:
        if not self.orders:
            return "(пусто)"
        return "\n".join(f"  [{i}] {o}" for i, o in enumerate(self.orders))


# ---------------------------
# Источник заявок (ИБ + ИЗ1)
# ---------------------------
class RestaurantSource:
    """
    ИБ + ИЗ1:
    - бесконечный источник (генерирует без остановки)
    - равномерный (детерминированный) интервал: через равные промежутки времени
      t = t0 + k * interval

    ВАЖНО:
    - чтобы не было "толпы" заявок строго в t=0 от всех источников,
      задаём ДЕТЕРМИНИРОВАННЫЙ стартовый сдвиг start_offset
      (например 0, interval/3, 2*interval/3 для 3 ресторанов).
      При этом интервал между заявками всё равно фиксированный и одинаковый.
    """

    def __init__(self, restaurant_id: int, interval: float, start_offset: float):
        if interval <= 0:
            raise ValueError("interval must be > 0 for IZ1")

        self.restaurant_id = restaurant_id
        self.interval = interval
        self.generated = 0

        # первый заказ в момент start_offset (может быть 0.0)
        self.next_time = start_offset

    def generate_event(self) -> Event:
        ev = Event(
            time=self.next_time,
            etype=EventType.ORDER_GENERATED,
            restaurant_id=self.restaurant_id,
            order_id=self.generated
        )
        self.generated += 1
        self.next_time += self.interval  # <-- ключ IZ1: строго фиксированный интервал
        return ev


# ---------------------------
# Оператор (П32: экспоненциальное время обслуживания)
# ---------------------------
class Operator:
    def __init__(self, operator_id: int, mean_service_time: float):
        if mean_service_time <= 0:
            raise ValueError("mean_service_time must be > 0")

        self.operator_id = operator_id
        self.mean_service_time = mean_service_time  # П32
        self.busy = False
        self.current_order: Optional[Order] = None

        # для Д2Б5: текущий "пакет" ресторана
        self.batch_restaurant_id: Optional[int] = None

    def start_service(self, order: Order, current_time: float) -> Event:
        self.busy = True
        self.current_order = order
        self.batch_restaurant_id = order.restaurant_id  # оператор закрепляется за пакетом

        # П32: экспоненциальное время обслуживания
        dt = random.expovariate(1.0 / self.mean_service_time)
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

    def free(self):
        self.busy = False
        self.current_order = None
        # batch_restaurant_id не сбрасываем: по Д2Б5 оператор старается продолжать пакет


# ---------------------------
# СМО: диспетчеры + календарь + статистика
# ---------------------------
class SMO:
    def __init__(
        self,
        num_restaurants: int = 3,
        num_operators: int = 2,
        interval: float = 5.0,          # ИЗ1: фиксированный межприход
        op_mean: float = 5.0,           # П32: среднее обслуживание
        buffer_cap: int = 5,
        seed: Optional[int] = None
    ):
        if seed is not None:
            random.seed(seed)

        self.time = 0.0
        self.buffer = Buffer(buffer_cap)
        self.operators = [Operator(i, op_mean) for i in range(num_operators)]

        # ДЕТЕРМИНИРОВАННЫЕ стартовые сдвиги (не ломают ИЗ1):
        # чтобы источники не "стреляли" синхронно, делим интервал на num_restaurants
        # и задаём равномерные оффсеты 0, interval/n, 2*interval/n, ...
        offsets = [(i * interval) / num_restaurants for i in range(num_restaurants)]
        self.restaurants = [
            RestaurantSource(i, interval, offsets[i]) for i in range(num_restaurants)
        ]

        # очередь событий
        self.event_queue: List[Event] = []
        self.last_events: List[Event] = []  # календарь

        # статистика
        self.total_generated = 0
        self.total_processed = 0
        self.total_rejected = 0
        self.wait_times = [[] for _ in range(num_restaurants)]

        # начальные события генерации
        for r in self.restaurants:
            heapq.heappush(self.event_queue, r.generate_event())

    # ---- Д2П1: выбор прибора (приоритет по номеру) ----
    def _get_free_operator_d2p1(self) -> Optional[Operator]:
        for op in sorted(self.operators, key=lambda o: o.operator_id):
            if not op.busy:
                return op
        return None

    # ---- Д2Б5: выбор заявок пакетами по источнику ----
    def _select_restaurant_for_batch(self) -> Optional[int]:
        rests = self.buffer.restaurants_present()
        return rests[0] if rests else None  # min id

    def _take_order_from_buffer_d2b5(self, op: Operator) -> Optional[Order]:
        if self.buffer.is_empty():
            return None

        # 1) продолжить текущий пакет
        if op.batch_restaurant_id is not None:
            o = self.buffer.pop_first_by_restaurant(op.batch_restaurant_id)
            if o is not None:
                return o

        # 2) выбрать новый самый приоритетный пакет
        new_rest = self._select_restaurant_for_batch()
        if new_rest is None:
            return None
        op.batch_restaurant_id = new_rest
        return self.buffer.pop_first_by_restaurant(new_rest)

    # ---- служебное ----
    def push_event(self, ev: Event):
        heapq.heappush(self.event_queue, ev)

    def _log(self, ev: Event):
        self.last_events.append(ev)

    # ---- шаг симуляции ----
    def step(self) -> bool:
        if not self.event_queue:
            return False

        ev = heapq.heappop(self.event_queue)
        self.time = ev.time
        self._log(ev)

        if ev.etype == EventType.ORDER_GENERATED:
            # учёт генерации (Д1ОО5: даже отказанную считаем)
            self.total_generated += 1

            # планируем следующее событие генерации этого источника (ИБ + ИЗ1)
            src = self.restaurants[ev.restaurant_id]
            self.push_event(src.generate_event())

            # новая заявка
            order = Order(ev.restaurant_id, ev.order_id, ev.time)

            # Д2П1: попытка сразу на свободный прибор
            op = self._get_free_operator_d2p1()
            if op is not None:
                self._log(Event(
                    time=self.time,
                    etype=EventType.ORDER_TO_OPERATOR,
                    restaurant_id=order.restaurant_id,
                    order_id=order.order_id,
                    operator_id=op.operator_id,
                    wait_time=0.0,
                    buffer_pos=-1
                ))
                self.push_event(op.start_service(order, self.time))
            else:
                # приборов нет — в буфер (Д1ОЗ2) либо отказ (Д1ОО5)
                pos = self.buffer.add_fifo(order)
                if pos != -1:
                    self._log(Event(
                        time=self.time,
                        etype=EventType.ORDER_TO_BUFFER,
                        restaurant_id=order.restaurant_id,
                        order_id=order.order_id,
                        buffer_pos=pos
                    ))
                else:
                    # отказ новой заявки, буфер не меняем
                    self.total_rejected += 1
                    self._log(Event(
                        time=self.time,
                        etype=EventType.ORDER_REJECTED,
                        restaurant_id=order.restaurant_id,
                        order_id=order.order_id,
                        buffer_pos=-1
                    ))

        elif ev.etype == EventType.OPERATOR_FREE:
            op = self.operators[ev.operator_id]
            op.free()

            self.total_processed += 1
            self.wait_times[ev.restaurant_id].append(ev.wait_time)

            # Д2Б5: после освобождения оператор пытается продолжить свой пакет
            next_order = self._take_order_from_buffer_d2b5(op)
            if next_order is not None:
                self._log(Event(
                    time=self.time,
                    etype=EventType.ORDER_TO_OPERATOR,
                    restaurant_id=next_order.restaurant_id,
                    order_id=next_order.order_id,
                    operator_id=op.operator_id,
                    wait_time=self.time - next_order.timestamp,
                    buffer_pos=-1
                ))
                self.push_event(op.start_service(next_order, self.time))
            # иначе оператор остаётся свободным

        return True

    # ---- выводы ----
    def print_state(self):
        print("\n=== ТЕКУЩЕЕ СОСТОЯНИЕ ===")
        print(f"Время: {self.time:.2f}")

        print("\nРестораны (ИБ + ИЗ1):")
        for r in self.restaurants:
            print(
                f"  Ресторан {r.restaurant_id}: interval={r.interval:.2f}, "
                f"next={r.next_time:.2f}, generated={r.generated}"
            )

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
            avg_wait = (sum(waits) / len(waits)) if waits else 0.0
            print(f"  Ресторан {i}: обработано={len(waits)}, ср. ожидание={avg_wait:.2f}")

    def print_calendar(self, last_n: int = 80):
        print("\n=== Последние события (ОД3) ===")
        tail = self.last_events[-last_n:] if last_n > 0 else self.last_events
        for ev in tail:
            print(ev)


# ---------------------------
# CLI
# ---------------------------
def main():
    print("=== СИМУЛЯЦИЯ СМО - ЦЕНТР ОБРАБОТКИ ЗАКАЗОВ ДОСТАВКИ ЕДЫ ===")

    # Параметры (можно менять под эксперимент):
    # interval — ИЗ1 (фиксированный интервал между заявками каждого ресторана)
    # op_mean — П32 (среднее время обслуживания)
    smo = SMO(
        num_restaurants=3,
        num_operators=2,
        interval=5.0,
        op_mean=5.0,
        buffer_cap=5,
        seed=None  # поставь число для воспроизводимости
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
