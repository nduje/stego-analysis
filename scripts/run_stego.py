"""Day 3 demo -- round-trip through the lib pipeline with a passphrase-derived key.

Flow: message -> AES-CTR (key from passphrase: scrypt -> HKDF) -> embed in PNG
-> extract -> AES-CTR^-1 -> message. No sockets.

Run (from the repo root):
    python -m scripts.run_stego
    python -m scripts.run_stego --cover data/covers/cover_noise.png --message "Hi" --passphrase "correct horse"
"""
import argparse

from lib.algorithm import StegAlgorithm, load_image
from lib.crypto import DEFAULT_PASSPHRASE


def run(cover_path, message, out_path, passphrase):
    alg = StegAlgorithm()

    hidden = alg.hide(message=message, cover_path=cover_path, out_path=out_path, passphrase=passphrase)
    if hidden is False:
        print(f"[FAIL] message too large for cover: {cover_path}")
        return False

    stego = load_image(out_path)
    recovered = alg.expose(stego_image=stego, passphrase=passphrase)

    ok = (recovered == message)
    status = "OK" if ok else "MISMATCH"
    print(f"[{status}] cover={cover_path}")
    print(f"        passphrase: {passphrase!r}")
    print(f"        sent      : {message!r}")
    print(f"        recovered : {recovered!r}")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cover", default="data/covers/cover_noise.png")
    ap.add_argument("--message", default="Hello!")
    ap.add_argument("--out", default="results/stego_lib.png")
    ap.add_argument("--passphrase", default=DEFAULT_PASSPHRASE)
    args = ap.parse_args()
    ok = run(args.cover, args.message, args.out, args.passphrase)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
