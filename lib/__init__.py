"""Parameterized steganography library.

The frozen `baseline/` package is the control group. `lib/` is a clean,
parameterized re-implementation whose DEFAULT configuration reproduces the
baseline 1:1 (byte-identical stego output). The parameters are exposed as
"switches" so the improvement phase can slot in new behavior without a rewrite;
every non-default switch is an inert hook that raises NotImplementedError.
"""
from lib.config import StegoConfig
from lib.algorithm import StegAlgorithm

__all__ = ["StegoConfig", "StegAlgorithm"]
