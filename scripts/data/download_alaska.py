"""Skida reproducibilan nasumičan podskup ALASKA v2 TIFF 256 COLOR nositelja.
Slike se serviraju preko http://; ako dođe do redirecta na https s isteklim
certifikatom, preskačemo provjeru (javni dataset, integritet provjerimo nakon).
"""
import os, ssl, random, time, urllib.request

DATASET = "ALASKA_v2_TIFF_256_COLOR"
BASE = f"http://alaska.utt.fr/DATASETS/{DATASET}"
TOTAL, N, SEED = 80005, 500, 42
OUT = os.path.join("data", "alaska", "raw_tif")

os.makedirs(OUT, exist_ok=True)
random.seed(SEED)
indices = sorted(random.sample(range(1, TOTAL + 1), N))

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE  # toleriraj istekli cert ako http redirecta na https

ok = 0
for i, idx in enumerate(indices, 1):
    name = f"{idx:05d}.tif"
    dest = os.path.join(OUT, name)
    if os.path.exists(dest):
        ok += 1; continue
    try:
        with urllib.request.urlopen(f"{BASE}/{name}", context=ctx, timeout=30) as r, open(dest, "wb") as f:
            f.write(r.read())
        ok += 1
    except Exception as e:
        print(f"[skip] {name}: {e}")
    if i % 50 == 0:
        print(f"{i}/{N} pokušano, {ok} ok")
    time.sleep(0.05)  # budi nježan prema njihovom serveru

print(f"Gotovo: {ok}/{N} slika u {OUT}")