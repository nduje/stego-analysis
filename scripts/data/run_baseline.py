"""Baseline demo -- the algorithm working end-to-end (round-trip).

Flow: message -> AES-CTR -> encode into PNG -> decode -> AES-CTR^-1 -> message.
No sockets; the key is a local stand-in (the library uses a derived key).

Run (from the repo root):
    python -m scripts.data.run_baseline
    python -m scripts.data.run_baseline --cover data/covers/cover_noise.png --message "Hello!"
"""
import argparse
import os
from baseline.stego import hide_message, expose_message
from baseline.image_utils import load_image
from baseline.crypto import generate_key


def run(cover_path, message, out_path, key=None):
    key = key or generate_key()

    hidden = hide_message(message=message, key=key, cover_path=cover_path, out_path=out_path)
    if hidden is False:
        print(f"[FAIL] message too large for cover: {cover_path}")
        return False

    stego = load_image(out_path)
    recovered = expose_message(hidden_message=stego, key=key)

    ok = (recovered == message)
    status = "OK" if ok else "MISMATCH"
    print(f"[{status}] cover={cover_path}")
    print(f"        sent      : {message!r}")
    print(f"        recovered : {recovered!r}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cover", default="data/covers/cover_noise.png")
    ap.add_argument("--message", default="Hello!")
    ap.add_argument("--out", default="results/_scratch/stego_baseline.png")
    args = ap.parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    ok = run(args.cover, args.message, args.out)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
