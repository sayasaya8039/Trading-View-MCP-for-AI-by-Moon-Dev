# Windows / Codex setup (0.1.1)

Python 3.12 and Google Chrome are recommended. This release pins the MCP SDK
to v1 because v2 removed the FastMCP import used by this server.

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -e '.[dev]' build
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
.venv/Scripts/python.exe -m tradingview_mcp.chrome_launcher
```

Sign into TradingView in the dedicated Chrome window. Keep this window open.
The profile persists across restarts. Do not copy your normal browser profile
or commit browser data or your local `.env` file.

Add the following to `%USERPROFILE%/.codex/config.toml`, replacing both paths:

```toml
# TradingView MCP configuration version: 0.1.1
[mcp_servers.tradingview]
command = "D:/path/to/repository/.venv/Scripts/python.exe"
args = ["-m", "tradingview_mcp.server"]
cwd = "D:/path/to/repository"
startup_timeout_sec = 30
tool_timeout_sec = 90
enabled = true

[mcp_servers.tradingview.env]
PYTHONUTF8 = "1"
PYTHONIOENCODING = "utf-8"
TV_MCP_CDP_PORT = "9333"
```

When using port 9333, also put `TV_MCP_CDP_PORT=9333` in the repository's
local `.env` before launching Chrome. Use the same port in both places.
Restart Codex after registration. `codex mcp get tradingview` verifies the
configuration; the actual server advertises 16 tools.

Try asking Codex to list the current chart indicators, or validate a Pine
script. Validation uses TradingView's compiler and does not require a browser
login. Editing or saving scripts requires the dedicated browser session.

For local regression checks, run the offline tests explicitly; the upstream
`test_vwap_star_live.py` changes a live chart and is not an offline smoke test.

```powershell
.venv/Scripts/python.exe -m pytest tests/test_smoke.py tests/test_windows_setup.py tests/test_chart_state.py -q
.venv/Scripts/python.exe -m build
```

## Lessons from verification

- Verify a real `tools/call`, not only `initialize` and `tools/list`: Chrome
  initializes lazily and previously printed protocol-breaking logs to stdout.
- Keep launcher diagnostics on stderr and configure UTF-8 on Windows.
- Test both fresh launch and connection reuse paths.
- Treat logged-out chart access and authenticated Pine Editor access as
  separate verification stages.

- Prefer active-chart getters over page titles/URLs for symbol and interval;
  handle each getter independently to retain partial results during loading.
