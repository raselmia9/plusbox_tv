import os
import time
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
    # স্ট্যাটাস ফাইল রিসেট করা
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Auto-Capture Log ---\n\n")

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
            time.sleep(5)

            # চ্যানেল কার্ডগুলো খুঁজে বের করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            log_status("debug", f"মোট চ্যানেল পাওয়া গেছে: {len(channel_links)} টি")

            for index, link in enumerate(channel_links):
                # ১. চ্যানেলের নাম বা টাইটেল সংগ্রহ
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

                # ৩. নেটওয়ার্ক রিকোয়েস্ট ট্র্যাক করার জন্য কন্টেইনার
                captured_m3u8 = []

                def handle_request(request):
                    if ".m3u8" in request.url or "playlist" in request.url:
                        if request.url not in captured_m3u8:
                            captured_m3u8.append(request.url)

                # রিকোয়েস্ট লিসেনার যুক্ত করা
                page.on("request", handle_request)

                try:
                    # ৪. চ্যানেলে স্বয়ংক্রিয় ক্লিক করা যাতে ভিডিও ও m3u8 লিংক লোড হয়
                    link.click()
                    # লিংক লোড হওয়ার জন্য ২ সেকেন্ড অপেক্ষা
                    time.sleep(2.5)
                except Exception as click_err:
                    log_status("warning", f"{title} এ ক্লিক করার সময় সমস্যা হয়েছে: {str(click_err)}")

                # লিসেনার রিমুভ করা পরবর্তী চ্যানেলের জন্য
                page.remove_listener("request", handle_request)

                # আসল m3u8 লিংক অ্যাসাইন করা
                stream_url = captured_m3u8[0] if captured_m3u8 else "https://plusbox.tv/"

                if logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })
                    log_status("success", f"[{title}] সফলভাবে ক্যাপচার হয়েছে!")

            # ৫. .m3u প্লেলিস্ট ফাইল তৈরি করা
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
