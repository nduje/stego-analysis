"""Hook tests: non-default switches are inert on Day 2.

Every non-default switch value must raise NotImplementedError (it's a reserved
hook), unknown values must raise ValueError, and the default config must
construct cleanly.

Run:
    python -m pytest tests/test_lib_hooks.py
    python tests/test_lib_hooks.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import StegoConfig

HOOKS = [
    {"matching_mode": "pm_one"},
    {"termination": "length_header"},
    {"saturation_255": "fix"},
    {"bits_per_channel": 2},
]
# note: pixel_order="prng" is now implemented (Improvement 1) -> no longer a hook


def test_default_config_constructs():
    StegoConfig()  # must not raise


def test_hooks_raise_not_implemented():
    for kwargs in HOOKS:
        try:
            StegoConfig(**kwargs)
        except NotImplementedError:
            continue
        raise AssertionError(f"expected NotImplementedError for {kwargs}")


def test_unknown_value_raises_value_error():
    try:
        StegoConfig(matching_mode="bogus")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown switch value")


if __name__ == "__main__":
    tests = [
        ("default config constructs", test_default_config_constructs),
        ("hooks raise NotImplementedError", test_hooks_raise_not_implemented),
        ("unknown value raises ValueError", test_unknown_value_raises_value_error),
    ]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
