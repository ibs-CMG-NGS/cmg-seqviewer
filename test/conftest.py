"""Shared pytest fixtures for the enrichment engine suite (plan §12, F1/G13)."""

import socket
import urllib.request

import pytest

import requests


@pytest.fixture
def block_network(monkeypatch):
    """Simulate a fully offline environment (plan F1: requests + urllib + socket).

    Used by `-m offline` tests to prove local paths never secretly depend on
    online APIs (plan principle 2, G9).
    """
    def _blocked(*args, **kwargs):
        raise requests.exceptions.ConnectionError(
            "network blocked by block_network fixture")

    # requests
    monkeypatch.setattr(requests.sessions.Session, "request", _blocked)
    monkeypatch.setattr(requests, "get", _blocked)
    monkeypatch.setattr(requests, "post", _blocked)

    # urllib
    def _urlopen_blocked(*args, **kwargs):
        raise OSError("network blocked by block_network fixture")
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_blocked)

    # socket (last-resort hard block)
    def _socket_connect(*args, **kwargs):
        raise OSError("network blocked by block_network fixture")
    monkeypatch.setattr(socket.socket, "connect", _socket_connect)

    yield
