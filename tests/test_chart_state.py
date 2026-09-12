"""Chart state must remain readable with current TradingView page titles."""
from types import SimpleNamespace

import pytest

from tradingview_mcp.tools.chart import _current_chart_state


@pytest.mark.parametrize(
    ("page", "symbol", "interval"),
    [
        # Live September 2026 page: price-only title and no query parameters.
        ({"title": "AAPL 332.27 ▲ +1.75%", "href": "https://www.tradingview.com/chart/",
          "symbol": "BATS:AAPL", "interval": "D"}, "BATS:AAPL", "D"),
        # The displayed chart takes precedence over stale title/URL metadata.
        ({"title": "NVDA, 5 — TradingView", "href": "https://www.tradingview.com/chart/?symbol=MSFT&interval=60",
          "symbol": "BATS:AAPL", "interval": "D"}, "BATS:AAPL", "D"),
        # Older clients or charts still initializing retain URL fallback.
        ({"title": "TradingView", "href": "https://www.tradingview.com/chart/?symbol=NASDAQ%3ANVDA&interval=60",
          "symbol": None, "interval": None}, "NASDAQ:NVDA", "60"),
        ({"title": "NVDA, 5 — TradingView", "href": "https://www.tradingview.com/chart/"}, "NVDA", "5"),
        # A partial getter response must not discard the successful field.
        ({"title": "TradingView", "href": "https://www.tradingview.com/chart/?interval=240",
          "symbol": "BATS:AAPL", "interval": ""}, "BATS:AAPL", "240"),
    ],
)
def test_chart_state_fallbacks(page, symbol, interval):
    client = SimpleNamespace(eval_js=lambda expression: page)
    assert _current_chart_state(client) == {
        "symbol": symbol, "interval": interval, "url": page["href"],
    }
