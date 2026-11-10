"""Fixtures for the tests that run inside a real Home Assistant.

They need `pytest-homeassistant-custom-component`, which brings Home Assistant with it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from fake_cooker import FakeCooker  # noqa: E402


@pytest.fixture(autouse=True)
def _custom_integrations(request: pytest.FixtureRequest) -> None:
    """Let Home Assistant load this integration. Skipped for tests that don't use Home Assistant."""
    if "hass" in request.fixturenames:
        request.getfixturevalue("enable_custom_integrations")


@pytest.fixture
def cooker(socket_enabled: None, monkeypatch: pytest.MonkeyPatch):
    """A pretend cooker on a local port, with the integration pointed at it."""
    from custom_components.tokit_cooker import miio

    with FakeCooker() as fake:
        monkeypatch.setattr(miio, "PORT", fake.port)
        yield fake
