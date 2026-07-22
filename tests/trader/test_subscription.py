from unittest.mock import Mock

from vnpy.trader.constant import Exchange
from vnpy.trader.engine import MainEngine
from vnpy.trader.object import SubscribeRequest


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
