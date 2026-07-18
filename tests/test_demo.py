"""Sanity for the demo's pure helpers -- the parts that decide what gets embedded.

The demo is optional: if Streamlit is not installed (the measurement pipeline does not need
it) this test skips instead of failing, so the suite stays runnable without demo extras.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.common import config_from_switches, switches_tag, payload_for_rate
except ImportError as exc:                      # streamlit (demo-only) not installed
    print(f"demo tests skipped: {exc}")
    sys.exit(0)

from lib.rates import capacity_chars, chars_for_rate


def test_switches_map_to_config():
    """Each switch flips exactly the field it is meant to flip."""
    base = config_from_switches(0, 0, 0)
    assert base.pixel_order == "sequential"
    assert base.matching_mode == "plus_one"
    assert base.termination == "continuation_flag"

    assert config_from_switches(1, 0, 0).pixel_order == "prng"
    assert config_from_switches(0, 1, 0).matching_mode == "pm_one"
    assert config_from_switches(0, 0, 1).termination == "length_header"

    allc = config_from_switches(1, 1, 1)
    assert (allc.pixel_order, allc.matching_mode, allc.termination) == \
           ("prng", "pm_one", "length_header")
    print("switch -> config mapping OK")


def test_switches_tag():
    assert switches_tag(0, 0, 0) == "000"
    assert switches_tag(1, 0, 1) == "101"
    assert switches_tag(True, True, True) == "111"
    print("switches tag OK")


def test_payload_fills_the_rate():
    """The message is repeated to exactly the character count that rate implies."""
    cap = capacity_chars(256, 256)
    for rate in (0.05, 0.25, 1.0):
        for header in (0, 2):
            n = chars_for_rate(cap, rate) - header
            p = payload_for_rate("abc", rate, 256, 256, header)
            assert len(p) == n, f"rate {rate} header {header}: {len(p)} != {n}"
            assert p.startswith("abc") or n < 3
    assert payload_for_rate("", 0.25) == ""       # empty message -> empty payload
    print("payload fills the rate OK")


if __name__ == "__main__":
    test_switches_map_to_config()
    test_switches_tag()
    test_payload_fills_the_rate()
    print("all demo tests passed")
