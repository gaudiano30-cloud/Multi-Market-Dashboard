from __future__ import annotations

import pytest

from secureapp.auth import AuthService
from secureapp.storage import Store


class FakeClock:
    """Drives both clocks used by AuthService (wall time and monotonic time)."""

    def __init__(self) -> None:
        self.now = 1_800_000_015.0  # in the middle of a 30-s TOTP step

    def wall(self) -> float:
        return self.now

    def mono(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "test.db")
    yield s
    s.close()


@pytest.fixture
def auth(store, clock) -> AuthService:
    return AuthService(store, clock=clock.wall, monotonic=clock.mono)
