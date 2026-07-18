"""Capture the demo's tabs to docs/demo/ -- the fallback if Streamlit will not start.

Drives a headless Chrome through the running demo, waits for each tab to finish rendering
(Streamlit paints a skeleton first, so a plain page-load screenshot would capture nothing),
and saves one PNG per tab. Requires the demo to be running and `selenium` installed:

    python -m streamlit run app/demo.py --server.port 8557
    python -m app.capture_screenshots --port 8557
"""
import argparse
import os
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

OUT_DIR = os.path.join("docs", "demo")
# (file name, tab index, a phrase that only appears once that tab has rendered)
SHOTS = [
    ("01-embedding.png", 0, "Nositelj i stego"),
    ("02-key.png", 1, "Ispravna zaporka"),
    ("03-order.png", 2, "Gdje algoritam dira piksele"),
    ("04-flag.png", 3, "Plavi kanal"),
    ("05-attacks.png", 4, "Napad na"),
    ("06-results.png", 5, "Glavna tablica"),
]


def _driver(width, height):
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--hide-scrollbars")
    opts.add_argument(f"--window-size={width},{height}")
    return webdriver.Chrome(options=opts)


def _wait_for_text(driver, phrase, timeout=90):
    WebDriverWait(driver, timeout).until(
        lambda d: phrase in d.find_element(By.TAG_NAME, "body").text)


def run(port, width, height):
    os.makedirs(OUT_DIR, exist_ok=True)
    driver = _driver(width, height)
    try:
        driver.get(f"http://localhost:{port}")
        _wait_for_text(driver, "Analiza detektabilnosti")      # app shell is up
        WebDriverWait(driver, 90).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[role="tab"]')))
        tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
        print(f"found {len(tabs)} tabs")

        for name, idx, phrase in SHOTS:
            tabs = driver.find_elements(By.CSS_SELECTOR, '[role="tab"]')
            driver.execute_script("arguments[0].click();", tabs[idx])
            try:
                _wait_for_text(driver, phrase)
            except TimeoutException:
                print(f"  ! {name}: '{phrase}' never appeared; capturing anyway")
            time.sleep(2.5)                                    # let images/plots paint
            path = os.path.join(OUT_DIR, name)
            driver.save_screenshot(path)
            print(f"  wrote {path} ({os.path.getsize(path):,} bytes)")
    finally:
        driver.quit()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8557)
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=1700)
    args = ap.parse_args()
    run(args.port, args.width, args.height)


if __name__ == "__main__":
    main()
