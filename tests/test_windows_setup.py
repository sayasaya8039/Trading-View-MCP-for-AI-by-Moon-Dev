"""Regression checks for Windows discovery and clean MCP stdio transport."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

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


def test_launcher_main_logs_only_to_stderr(monkeypatch, capsys):
    monkeypatch.setattr(chrome_launcher, "launch_chrome", lambda: None)
    assert chrome_launcher.main() == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "dedicated Chrome is running" in captured.err


def test_explicit_chrome_binary_overrides_discovery(monkeypatch):
    monkeypatch.setattr(chrome_launcher, "CHROME_BINARY_OVERRIDE", "D:/Chrome/chrome.exe")
    monkeypatch.setattr(chrome_launcher.platform, "system", Mock(side_effect=AssertionError))
    assert chrome_launcher.find_chrome_binary() == "D:/Chrome/chrome.exe"


@pytest.mark.parametrize("system,expected", [
    ("Darwin", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
    ("Linux", "/usr/bin/chromium"),
    ("Windows", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
])
def test_chrome_platform_discovery(monkeypatch, system, expected):
    monkeypatch.setattr(chrome_launcher, "CHROME_BINARY_OVERRIDE", "")
    monkeypatch.setattr(chrome_launcher.platform, "system", lambda: system)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.setattr(chrome_launcher.shutil, "which", lambda name: expected if name == "chromium" else None)
    monkeypatch.setattr(Path, "exists", lambda path: path == Path(expected))
    assert chrome_launcher.find_chrome_binary() == expected


def test_missing_chrome_reports_override_setting(monkeypatch):
    monkeypatch.setattr(chrome_launcher, "CHROME_BINARY_OVERRIDE", "")
    monkeypatch.setattr(chrome_launcher.platform, "system", lambda: "Windows")
    monkeypatch.setattr(Path, "exists", lambda path: False)
    with pytest.raises(FileNotFoundError, match="TV_MCP_CHROME_BINARY"):
        chrome_launcher.find_chrome_binary()


@pytest.mark.parametrize("skip,occupied,message", [
    (True, False, "TV_MCP_SKIP_CHROME_LAUNCH"),
    (False, True, "doesn't look like Chrome CDP"),
])
def test_unavailable_cdp_never_launches_wrong_browser(monkeypatch, skip, occupied, message):
    spawn = Mock(side_effect=AssertionError("unexpected browser launch"))
    monkeypatch.setattr(chrome_launcher, "cdp_is_ready", lambda: False)
    monkeypatch.setattr(chrome_launcher, "TV_MCP_SKIP_LAUNCH", skip)
    monkeypatch.setattr(chrome_launcher, "port_is_open", lambda port: occupied)
    monkeypatch.setattr(chrome_launcher.subprocess, "Popen", spawn)
    with pytest.raises(RuntimeError, match=message):
        chrome_launcher.launch_chrome()
    spawn.assert_not_called()


@pytest.mark.parametrize("wait_ready", [False, True])
def test_launch_without_wait_or_with_expired_deadline(monkeypatch, tmp_path, wait_ready):
    process = object()
    monkeypatch.setattr(chrome_launcher, "cdp_is_ready", lambda: False)
    monkeypatch.setattr(chrome_launcher, "TV_MCP_SKIP_LAUNCH", False)
    monkeypatch.setattr(chrome_launcher, "port_is_open", lambda port: False)
    monkeypatch.setattr(chrome_launcher, "PROFILE_DIR", tmp_path / "profile")
    monkeypatch.setattr(chrome_launcher, "find_chrome_binary", lambda: "chrome.exe")
    monkeypatch.setattr(chrome_launcher.subprocess, "Popen", lambda *a, **kw: process)
    if wait_ready:
        with pytest.raises(RuntimeError, match="did not open CDP port"):
            chrome_launcher.launch_chrome(wait_ready=True, wait_seconds=0)
    else:
        assert chrome_launcher.launch_chrome(wait_ready=False) is process


@pytest.mark.parametrize("status", [200, 404])
def test_cdp_health_and_browser_name(monkeypatch, status):
    response = SimpleNamespace(status_code=status, json=lambda: {"Browser": "Chrome/test"})
    request = Mock(return_value=response)
    monkeypatch.setattr(chrome_launcher.requests, "get", request)
    assert chrome_launcher.cdp_is_ready(19333) is (status == 200)
    assert chrome_launcher.cdp_browser_name(19333) == ("Chrome/test" if status == 200 else "")
    assert request.call_args.args == ("http://127.0.0.1:19333/json/version",)


def test_cdp_connection_failure_is_unavailable(monkeypatch):
    request = Mock(side_effect=chrome_launcher.requests.ConnectionError("offline"))
    monkeypatch.setattr(chrome_launcher.requests, "get", request)
    assert chrome_launcher.cdp_is_ready() is False
    assert chrome_launcher.cdp_browser_name() == ""
