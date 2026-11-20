"""Unit tests for the positioning math.

These tests run on the host (CPython) by stubbing the MicroPython
machine module, so the layout logic can be verified without hardware.
"""

import sys
import types

# Stub the MicroPython 'machine' module for host testing
machine = types.ModuleType("machine")


class _Pin:
    # MicroPython Pin mode/pull constants used at module import time
    OUT = 3
    IN = 1
    PULL_UP = 2

    def __init__(self, *args, **kwargs):
        self._value = 1

    def value(self, v=None):
        if v is None:
            return self._value
        self._value = v


machine.Pin = _Pin


# time.sleep_us only exists on MicroPython; stub it for host testing
import time  # noqa: E402

if not hasattr(time, "sleep_us"):
    time.sleep_us = lambda us: None
sys.modules["machine"] = machine

sys.path.insert(0, "src")
import motion  # noqa: E402


def test_steps_per_mm():
    assert motion.STEPS_PER_MM == 400.0


def test_layout_positions_count():
    positions = motion.layout_positions(4, 40, 60)
    assert len(positions) == 4


def test_layout_positions_values():
    positions = motion.layout_positions(4, 40, 60)
    assert positions == [60, 100, 140, 180]


def test_layout_single_joint():
    positions = motion.layout_positions(1, 40, 60)
    assert positions == [60]
