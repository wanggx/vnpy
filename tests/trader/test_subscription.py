from unittest.mock import Mock

from vnpy.event import Event
from vnpy.trader.constant import Exchange
from vnpy.trader.engine import MainEngine, OmsEngine
from vnpy.trader.event import EVENT_TICK_UNSUBSCRIBE
from vnpy.trader.object import SubscribeRequest, TickData


def test_subscribe_request_subscriber_defaults() -> None:
    req: SubscribeRequest = SubscribeRequest("rb2501", Exchange.SHFE)

    assert req.vt_symbol == "rb2501.SHFE"
    assert req.app_name == "default"
    assert req.subscriber_name == "default"


def test_main_engine_unsubscribe_routes_request() -> None:
    gateway: Mock = Mock()
    engine: MainEngine = MainEngine.__new__(MainEngine)
    engine.gateways = {"TEST": gateway}
    engine.write_log = Mock()

    req: SubscribeRequest = SubscribeRequest(
        symbol="rb2501",
        exchange=Exchange.SHFE,
        app_name="CtaStrategy",
        subscriber_name="trend"
    )
    engine.unsubscribe(req, "TEST")

    gateway.unsubscribe.assert_called_once_with(req)


def test_oms_engine_removes_tick_on_unsubscribe() -> None:
    engine: OmsEngine = OmsEngine.__new__(OmsEngine)
    tick: TickData = TickData(
        symbol="rb2501",
        exchange=Exchange.SHFE,
        datetime=Mock(),
        gateway_name="TEST",
    )
    engine.ticks = {tick.vt_symbol: tick}

    req: SubscribeRequest = SubscribeRequest("rb2501", Exchange.SHFE)
    engine.process_tick_unsubscribe_event(Event(EVENT_TICK_UNSUBSCRIBE, req))

    assert tick.vt_symbol not in engine.ticks
