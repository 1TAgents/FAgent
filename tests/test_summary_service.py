from agents.services.summary import SummaryService


def test_clean_title_localizes_capability_smoke_title():
    service = SummaryService()

    assert service._clean_title("Title: capability qa smoke") == "能力问答测试"


def test_clean_title_localizes_stream_smoke_title():
    service = SummaryService()

    assert service._clean_title("frontend_proxy_stream_smoke") == "前端流式代理测试"


def test_fallback_title_localizes_english_internal_title():
    service = SummaryService()

    title = service._fallback_title([{"role": "user", "content": "capability qa smoke"}])

    assert title == "能力问答测试"


def test_localize_from_messages_short_circuits_internal_english_title():
    service = SummaryService()

    title = service._localize_from_messages(
        [
            {"role": "user", "content": "capability qa smoke"},
            {"role": "assistant", "content": "可以查询行情，也支持回测。"},
        ]
    )

    assert title == "能力问答测试"
