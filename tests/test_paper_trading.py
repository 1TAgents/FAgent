from agents.trading import PaperTradingService


def test_paper_trading_buy_and_sell_updates_account(tmp_path):
    service = PaperTradingService(str(tmp_path / "paper.db"))

    buy = service.place_order(symbol="600519", side="buy", quantity=100, price=100.0)

    assert buy["success"] is True
    assert buy["order"]["status"] == "filled"
    assert buy["snapshot"]["positions"][0]["symbol"] == "600519"
    assert buy["snapshot"]["positions"][0]["quantity"] == 100
    assert buy["snapshot"]["cash"] < 1_000_000

    sell = service.place_order(symbol="600519", side="sell", quantity=100, price=110.0)

    assert sell["success"] is True
    assert sell["order"]["status"] == "filled"
    assert sell["snapshot"]["positions"] == []
    assert sell["snapshot"]["total_value"] > buy["snapshot"]["total_value"]


def test_paper_trading_rejects_invalid_orders(tmp_path):
    service = PaperTradingService(str(tmp_path / "paper.db"))

    odd_lot = service.place_order(symbol="600519", side="buy", quantity=50, price=100.0)
    short_sell = service.place_order(symbol="600519", side="sell", quantity=100, price=100.0)

    assert odd_lot["success"] is False
    assert odd_lot["order"]["status"] == "rejected"
    assert "100 股整数倍" in odd_lot["error"]
    assert short_sell["success"] is False
    assert "持仓不足" in short_sell["error"]


def test_cancel_filled_order_is_rejected(tmp_path):
    service = PaperTradingService(str(tmp_path / "paper.db"))
    result = service.place_order(symbol="600519", side="buy", quantity=100, price=100.0)

    cancel = service.cancel_order(result["order"]["order_id"])

    assert cancel["success"] is False
    assert "不能撤单" in cancel["error"]
