"""Regression checks for Windows discovery and clean MCP stdio transport."""
from pathlib import Path
from types import SimpleNamespace

from tradingview_mcp import cdp_client, chrome_launcher


def test_windows_finds_user_chrome(monkeypatch, tmp_path):
    chrome = tmp_path / "Google/Chrome/Application/chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.touch()
    monkeypatch.setattr(chrome_launcher, "CHROME_BINARY_OVERRIDE", "")
    monkeypatch.setattr(chrome_launcher.platform, "system", lambda: "Windows")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # Model a machine where Chrome is installed only for the current user.
    monkeypatch.setattr(Path, "exists", lambda path: path == chrome)
    assert Path(chrome_launcher.find_chrome_binary()) == chrome


def test_reusing_chrome_keeps_mcp_stdout_clean(monkeypatch, capsys):
    monkeypatch.setattr(chrome_launcher, "cdp_is_ready", lambda: True)
    monkeypatch.setattr(chrome_launcher, "cdp_browser_name", lambda: "Chrome/test")
    assert chrome_launcher.launch_chrome() is None
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "reusing" in captured.err


def test_launching_chrome_keeps_mcp_stdout_clean(monkeypatch, tmp_path, capsys):
    ready = iter([False, True])
    monkeypatch.setattr(chrome_launcher, "cdp_is_ready", lambda: next(ready))
    monkeypatch.setattr(chrome_launcher, "port_is_open", lambda port: False)
    monkeypatch.setattr(chrome_launcher, "TV_MCP_SKIP_LAUNCH", False)
    monkeypatch.setattr(chrome_launcher, "PROFILE_DIR", tmp_path / "profile")
    monkeypatch.setattr(chrome_launcher, "find_chrome_binary", lambda: "chrome.exe")
    process = object()
    calls = []

    def launch(args, **kwargs):
        calls.append((args, kwargs))
        return process

    monkeypatch.setattr(chrome_launcher.subprocess, "Popen", launch)
    assert chrome_launcher.launch_chrome() is process
    assert "--remote-debugging-address=127.0.0.1" in calls[0][0]
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "launching dedicated Chrome" in captured.err
    assert "CDP ready" in captured.err


def test_app_discovery_keeps_mcp_stdout_clean(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cdp_client, "_moondev_ctrl_cache", "unset")
    monkeypatch.setattr(cdp_client, "MOONDEV_ENDPOINT_FILE", tmp_path / "absent.json")
    monkeypatch.delenv(cdp_client.MOONDEV_CTRL_ENV, raising=False)
    response = SimpleNamespace(ok=True, json=lambda: {"app": "Moon Dev Code App"})
    monkeypatch.setattr(cdp_client.requests, "get", lambda *args, **kwargs: response)
    assert cdp_client.moondev_control_url() == cdp_client.MOONDEV_CTRL_DEFAULT
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "driving the Code App browser" in captured.err
