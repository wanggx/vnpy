"""
Event-driven framework of VeighNa framework.
"""

import traceback
from collections import defaultdict
from collections.abc import Callable
from queue import Empty, Queue
from threading import Thread
from time import sleep, monotonic
from typing import Any


EVENT_TIMER = "eTimer"

# 兜底日志：同一 (事件类型, 异常类型, 出错位置) 在此间隔内只报一次，避免刷屏
HANDLER_ERROR_LOG_INTERVAL: float = 5.0


class Event:
    """
    Event object consists of a type string which is used
    by event engine for distributing event, and a data
    object which contains the real data.
    """

    def __init__(self, type: str, data: Any = None) -> None:
        """"""
        self.type: str = type
        self.data: Any = data


# Defines handler function to be used in event engine.
HandlerType = Callable[[Event], None]


class EventEngine:
    """
    Event engine distributes event object based on its type
    to those handlers registered.

    It also generates timer event by every interval seconds,
    which can be used for timing purpose.
    """

    def __init__(self, interval: int = 1) -> None:
        """
        Timer event is generated every 1 second by default, if
        interval not specified.
        """
        self._interval: int = interval
        self._queue: Queue = Queue()
        self._active: bool = False
        self._thread: Thread = Thread(target=self._run)
        self._timer: Thread = Thread(target=self._run_timer)
        self._handlers: defaultdict = defaultdict(list)
        self._general_handlers: list = []
        # handler 异常兜底日志的限流时间戳
        self._handler_error_at: dict[str, float] = {}
        # 日志输出钩子：由 MainEngine 注入 write_log（界面日志栏 + 日志文件）
        self.log_func: Callable[[str], Any] | None = None

    def _run(self) -> None:
        """
        Get event from queue and then process it.

        单个 handler 抛出的异常绝不能让本线程退出：事件引擎是整个应用的中枢，
        线程一死，所有事件（委托/成交/持仓/日志/定时任务）都会积压在队列里，
        整个 vnpy 客户端随即"假死"。所以这里做整体兜底：异常交给主引擎
        write_log 输出后，继续处理下一个事件。
        """
        while self._active:
            try:
                event: Event = self._queue.get(block=True, timeout=1)
            except Empty:
                continue

            if not self._active:
                break

            try:
                self._process(event)
            except Exception as ex:  # noqa: BLE001 - 兜底，见方法注释
                self._report_handler_error(event, ex)

    def _report_handler_error(self, event: Event, ex: BaseException) -> None:
        """把 handler 异常交给主引擎 write_log 输出（同一异常限流，避免刷屏）。"""
        log_func = self.log_func
        if log_func is None:
            return

        frame = traceback.extract_tb(ex.__traceback__)[-1] if ex.__traceback__ else None
        where: str = (
            f"{frame.filename}:{frame.lineno} in {frame.name}" if frame else "unknown"
        )
        key: str = f"{event.type}|{type(ex).__name__}|{where}"
        now: float = monotonic()
        if now - self._handler_error_at.get(key, 0.0) < HANDLER_ERROR_LOG_INTERVAL:
            return
        self._handler_error_at[key] = now

        message: str = (
            f"事件处理异常已隔离，事件引擎继续运行：type={event.type} "
            f"{type(ex).__name__}: {ex} @ {where}"
        )
        try:
            log_func(message)
        except Exception:  # noqa: BLE001 - 日志输出失败也不能影响事件分发
            pass

    def _process(self, event: Event) -> None:
        """
        First distribute event to those handlers registered listening
        to this type.

        Then distribute event to those general handlers which listens
        to all types.
        """
        if event.type in self._handlers:
            [handler(event) for handler in self._handlers[event.type]]

        if self._general_handlers:
            [handler(event) for handler in self._general_handlers]

    def _run_timer(self) -> None:
        """
        Sleep by interval second(s) and then generate a timer event.
        """
        while self._active:
            sleep(self._interval)
            event: Event = Event(EVENT_TIMER)
            self.put(event)

    def start(self) -> None:
        """
        Start event engine to process events and generate timer events.
        """
        self._active = True
        self._thread.start()
        self._timer.start()

    def stop(self) -> None:
        """
        Stop event engine.
        """
        self._active = False
        self._timer.join()
        self._thread.join()

    def put(self, event: Event) -> None:
        """
        Put an event object into event queue.
        """
        self._queue.put(event)

    def register(self, type: str, handler: HandlerType) -> None:
        """
        Register a new handler function for a specific event type. Every
        function can only be registered once for each event type.
        """
        handler_list: list = self._handlers[type]
        if handler not in handler_list:
            handler_list.append(handler)

    def unregister(self, type: str, handler: HandlerType) -> None:
        """
        Unregister an existing handler function from event engine.
        """
        handler_list: list = self._handlers[type]

        if handler in handler_list:
            handler_list.remove(handler)

        if not handler_list:
            self._handlers.pop(type)

    def register_general(self, handler: HandlerType) -> None:
        """
        Register a new handler function for all event types. Every
        function can only be registered once for each event type.
        """
        if handler not in self._general_handlers:
            self._general_handlers.append(handler)

    def unregister_general(self, handler: HandlerType) -> None:
        """
        Unregister an existing general handler function.
        """
        if handler in self._general_handlers:
            self._general_handlers.remove(handler)
