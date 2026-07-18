# Demo screenshots

Fallback for the defence: if Streamlit will not start on the presentation machine, these
images show what the demo does. Capture them once from a running demo
(`python -m streamlit run app/demo.py`) and drop the PNGs in this folder.

Suggested five, with the settings to use:

| file | tab | settings | what it should show |
|------|-----|----------|---------------------|
| `01-embedding.png` | 1 · Ugradnja | rate 0.25, no switches | cover vs stego side by side, the ×50 difference, the touched-pixel heat-map, and the live PSNR/SSIM numbers |
| `02-key.png` | 2 · Ključ | any | the message recovered with the right passphrase, noise with a wrong one |
| `03-order.png` | 3 · Raspored (P1) | rate 0.25 | the two heat-maps: sequential is packed at the top with a sharp edge, PRNG is scattered |
| `04-flag.png` | 4 · Zastavica (P3) | rate 0.5 | the blue-channel odd-value bias present with the flag and gone without it |
| `05-attacks.png` | 5 · Napadi uživo | rate 1.0, no switches | the chi-square inversion (stego scores *below* the cover) plus the measured distributions with the marker for this image |

A short screen recording of the same five views works just as well.
