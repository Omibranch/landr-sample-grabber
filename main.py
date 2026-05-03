import asyncio
import os
import re
import json
import time
from pathlib import Path
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
PROXY_SERVER = os.getenv("PROXY_SERVER", "")
PROXY_USER   = os.getenv("PROXY_USER", "")
PROXY_PASS   = os.getenv("PROXY_PASS", "")

DOWNLOAD_DIR = "landr_samples"
PAGE_LOAD_DELAY = 8000
SAMPLE_CLICK_DELAY = 0.3
MAX_RETRIES = 3
RETRY_DELAY = 2.0
TEST_MODE_2_ONLY = False

ASCII_ART = r"""
  _        _    _   _  ____   ____
 | |      / \  | \ | ||  _ \ |  _ \
 | |     / _ \ |  \| || | | || |_) |
 | |___ / ___ \| |\  || |_| ||  _ <
 |_____/_/   \_\_| \_||____/ |_| \_\
      S A M P L E   G R A B B E R
"""

Path(DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)

# ── helpers ──────────────────────────────────────────────────────────────────

def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()

def make_unique_path(folder: str, name: str, ext: str) -> str:
    base = os.path.join(folder, f"{name}{ext}")
    if not os.path.exists(base):
        return base
    counter = 1
    while True:
        candidate = os.path.join(folder, f"{name} ({counter}){ext}")
        if not os.path.exists(candidate):
            return candidate
        counter += 1

def ext_from_url(url: str) -> str:
    clean = url.split("?")[0]
    if clean.endswith(".wav"):
        return ".wav"
    if clean.endswith(".flac"):
        return ".flac"
    return ".mp3"

async def get_sample_name(row) -> str:
    # Primary: span[data-original] — LANDR stores the real filename here
    # (inner text is middle-truncated, attribute has the full value)
    el = await row.query_selector("span[data-original]")
    if el:
        val = await el.get_attribute("data-original")
        if val and val.strip():
            return sanitize(val.strip())

    # Fallback: any non-empty span text that looks like a name (not a tag/number)
    for selector in ['span[class*="Text"]', 'span[class*="w_full"]', 'span[class*="bold"]']:
        el = await row.query_selector(selector)
        if el:
            text = (await el.inner_text()).strip()
            if text and len(text) > 2 and not text.isdigit():
                return sanitize(text)

    return "unknown"


async def download_with_retry(page, audio_url: str, dest_path: str) -> bool:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = await page.request.get(audio_url)
            if resp.ok:
                Path(dest_path).write_bytes(await resp.body())
                return True
            print(f"    [!] HTTP {resp.status} on attempt {attempt}")
        except Exception as e:
            print(f"    [!] Download error attempt {attempt}: {e}")
        if attempt < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY)
    return False


# ── main ─────────────────────────────────────────────────────────────────────

async def scrape_landr():
    print(ASCII_ART)

    target_url = input("Enter the LANDR Pack URL: ").strip()
    if not target_url:
        print("[!] URL cannot be empty.")
        return

    stats = {"downloaded": 0, "skipped": 0, "failed": 0}
    manifest_path = os.path.join(DOWNLOAD_DIR, "_manifest.json")
    manifest: dict = {}
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            manifest = json.load(f)

    async with async_playwright() as pw:
        proxy_config = (
            {"server": PROXY_SERVER, "username": PROXY_USER, "password": PROXY_PASS}
            if PROXY_SERVER else None
        )
        print(f"[*] Launching browser" + (f" via proxy: {PROXY_SERVER}" if proxy_config else " (no proxy)"))
        browser = await pw.chromium.launch(
            headless=False,
            **({"proxy": proxy_config} if proxy_config else {}),
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        print(f"[*] Navigating to: {target_url}")
        await page.goto(target_url)
        print(f"[*] Waiting {PAGE_LOAD_DELAY / 1000}s for interface …")
        await page.wait_for_timeout(PAGE_LOAD_DELAY)

        # ── pagination ───────────────────────────────────────────────────────
        max_page = 1
        if not TEST_MODE_2_ONLY:
            for link in await page.query_selector_all('a[href*="page="]'):
                href = await link.get_attribute("href")
                m = re.search(r"page=(\d+)", href)
                if m:
                    max_page = max(max_page, int(m.group(1)))

        print(f"[+] Pages to process: {max_page}\n")

        # ── per-page loop ────────────────────────────────────────────────────
        for p_num in range(1, max_page + 1):
            if TEST_MODE_2_ONLY and stats["downloaded"] >= 2:
                break

            if p_num > 1:
                curr_url = re.sub(r"[?&]page=\d+", "", target_url)
                sep = "&" if "?" in curr_url else "?"
                await page.goto(f"{curr_url}{sep}page={p_num}")
                await page.wait_for_timeout(PAGE_LOAD_DELAY)

            rows = await page.query_selector_all('div[class*="samplesMFE-Table__row"]')
            if not rows:
                # broader fallback selector
                rows = await page.query_selector_all('div[class*="Table__row"]')
            print(f"[*] Page {p_num}: {len(rows)} rows found")

            for row in rows:
                if TEST_MODE_2_ONLY and stats["downloaded"] >= 2:
                    break

                try:
                    sample_name = await get_sample_name(row)

                    play_btn = await row.query_selector('button[aria-label="Play"]')
                    if not play_btn:
                        play_btn = await row.query_selector('button[aria-label*="play" i]')
                    if not play_btn:
                        continue

                    # ── catch audio URL ──────────────────────────────────────
                    audio_url = None
                    for attempt in range(1, MAX_RETRIES + 1):
                        try:
                            async with page.expect_response(
                                lambda r: (
                                    "assets.landr.com" in r.url
                                    or "/samples/" in r.url
                                    or r.url.endswith(".mp3")
                                    or r.url.endswith(".wav")
                                ),
                                timeout=8000,
                            ) as resp_info:
                                await play_btn.click()
                            audio_url = (await resp_info.value).url
                            break
                        except Exception:
                            if attempt < MAX_RETRIES:
                                await asyncio.sleep(RETRY_DELAY)

                    if not audio_url:
                        print(f"    [!] No stream caught for: {sample_name}")
                        stats["failed"] += 1
                        continue

                    ext = ext_from_url(audio_url)
                    dest = make_unique_path(DOWNLOAD_DIR, sample_name, ext)
                    short = os.path.basename(dest)

                    # skip if already in manifest with same URL
                    if sample_name in manifest and manifest[sample_name] == audio_url:
                        if os.path.exists(dest):
                            print(f"    [=] Skip (exists): {short}")
                            stats["skipped"] += 1
                            await play_btn.click()  # stop playback
                            await asyncio.sleep(SAMPLE_CLICK_DELAY)
                            continue

                    print(f"    [>] {short}")
                    ok = await download_with_retry(page, audio_url, dest)
                    if ok:
                        stats["downloaded"] += 1
                        manifest[sample_name] = audio_url
                    else:
                        print(f"    [✗] Failed: {short}")
                        stats["failed"] += 1

                    # stop playback
                    try:
                        await play_btn.click()
                    except Exception:
                        pass
                    await asyncio.sleep(SAMPLE_CLICK_DELAY)

                except Exception as e:
                    print(f"    [!] Row error: {e}")
                    continue

        await browser.close()

    # save manifest
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(
        f"\n[DONE]  downloaded={stats['downloaded']}  "
        f"skipped={stats['skipped']}  failed={stats['failed']}"
    )


if __name__ == "__main__":
    asyncio.run(scrape_landr())
