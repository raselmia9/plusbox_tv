import os
import re
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"

def log_status(level, message):
    dots = {
        "info": "🔵 [INFO]",
        "success": "🟢 [SUCCESS]",
        "warning": "🟡 [WARNING]",
        "error": "🔴 [ERROR]",
        "debug": "🟣 [DEBUG]"
    }
    prefix = dots.get(level, "⚪ [LOG]")
    log_msg = f"{prefix} {message}"
    print(log_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def scrape_channels():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Direct-Pattern Playlist Generator ---\n\n")

    log_status("info", "স্ক্রিপ্ট শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            log_status("info", f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")

            # চ্যানেল কার্ডগুলো খুঁজে বের করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            log_status("debug", f"মোট চ্যানেল পাওয়া গেছে: {len(channel_links)} টি")

            for index, link in enumerate(channel_links):
                # ১. চ্যানেলের নাম সংগ্রহ
                data_name = link.get_attribute("data-name")
                href = link.get_attribute("href")
                title = data_name if data_name else (href.replace("#", "").strip() if href else f"Channel {index+1}")

                # ২. লোগো সংগ্রহ
                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        logo_url = "https://plusbox.tv" + src if src.startswith("/") else src

                # ৩. data-source লিংক সংগ্রহ
                data_source = link.get_attribute("data-source")

                if data_source:
                    # প্যাটার্ন অনুযায়ী .m3u8 এবং Referer লিংক তৈরি করা
                    # উদাহরণ data-source: https://backend.plusbox.tv/BTVWorld/embed.html?token=...
                    # রূপান্তর: https://backend.plusbox.tv/BTVWorld/index.fmp4.m3u8?token=...|Referer=...
                    
                    match = re.search(r'https://backend\.plusbox\.tv/([^/]+)/embed\.html\?(.*)', data_source)
                    if match:
                        channel_path = match.group(1)
                        query_params = match.group(2)
                        
                        # আপনার দেওয়া নিখুঁত ফরম্যাট
                        stream_url = f"https://backend.plusbox.tv/{channel_path}/index.fmp4.m3u8?{query_params}|Referer={data_source}"
                    else:
                        stream_url = data_source

                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })
                    log_status("success", f"[{title}] সফলভাবে প্রসেস করা হয়েছে!")
                else:
                    log_status("warning", f"[{title}] এর জন্য কোনো data-source পাওয়া যায়নি।")

            # ৪. .m3u প্লেলিস্ট ফাইল তৈরি করা
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in extracted_channels:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                    f.write(f'{ch["url"]}\n')

            log_status("success", f"প্লেলিস্ট সফলভাবে তৈরি হয়েছে! মোট চ্যানেল: {len(extracted_channels)}")

        except Exception as e:
            log_status("error", f"ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("info", "প্রসেস শেষ হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
