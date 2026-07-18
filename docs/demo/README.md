# Demo screenshots

Fallback for the defence: if Streamlit will not start on the presentation machine, these
images show what the demo does. One PNG per tab, captured from a running demo. (The demo
interface itself is in Croatian; the tabs are listed here in order.)

| file | tab | what it shows |
|------|-----|---------------|
| `01-embedding.png` | 1 — embedding | cover and stego side by side, the difference amplified x50 (the +/-1 noise, and the sharp edge where sequential embedding stops), the touched-pixel heat-map, and the live PSNR/SSIM/MSE |
| `02-key.png` | 2 — key | the message recovered with the right passphrase, noise with a wrong one |
| `03-order.png` | 3 — block order (P1) | the two heat-maps: sequential packed at the top with a sharp edge, PRNG scattered -- the same amount written, placed differently |
| `04-flag.png` | 4 — continuation flag (P3) | the odd-value bias in the blue channel, present with the flag and gone without it |
| `05-attacks.png` | 5 — live attacks | the chi-square inversion (stego scores fall *below* the covers) with the measured distributions and a marker for this image |
| `06-results.png` | 6 — results | the main table, the central figures, and the conclusion |

## Regenerating them

They are captured automatically (headless Chrome via Selenium), so they can be refreshed
whenever the demo changes:

```bash
python -m streamlit run app/demo.py --server.port 8558     # in one shell
python -m app.capture_screenshots --port 8558              # in another
```

Defaults are used for every shot (cover `00054.png`, rate 0.25, no switches enabled), so
the set is reproducible. `selenium` is only needed for this capture step, not for running
the demo.
