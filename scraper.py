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
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Dynamic Token m3u8 Capture Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        # headless=False দিয়ে দেখতে পারেন ব্রাউজারে কি হচ্ছে
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            log_status("info", f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            log_status("debug", f"মোট চ্যানেল পাওয়া গেছে: {len(channel_links)} টি")

            for index, link in enumerate(channel_links):
                data_name = link.get_attribute("data-name")
                href = link.get_attribute("href")
                title = data_name if data_name else (href.replace("#", "").strip() if href else f"Channel {index+1}")

                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        logo_url = "https://plusbox.tv" + src if src.startswith("/") else src

                captured_m3u8 = []

                # নেটওয়ার্ক রিকোয়েস্ট ইন্টারসেপ্ট করার ফাংশন
                def handle_request(request):
                    req_url = request.url
                    # যখনই টোকেনসহ m3u8 বা fmp4 রিকোয়েস্ট যাবে, সেটা ক্যাচ করবে
                    if (".m3u8" in req_url or ".fmp4" in req_url) and "token=" in req_url:
                        if req_url not in captured_m3u8:
                            captured_m3u8.append(req_url)

                page.on("request", handle_request)

                try:
                    # হোমপেজে চ্যানেলের থাম্বনেইলে ক্লিক করা, যা জাভাস্ক্রিপ্ট দিয়ে ডাইনামিক টোকেন এনে প্লেয়ারে লোড করবে
                    link.click()
                    # টোকেন জেনারেট হয়ে স্ট্রিম রিকোয়েস্ট সার্ভার থেকে আসার জন্য ৩ সেকেন্ড সময় দেওয়া
                    time.sleep(3.5)
                except Exception as click_err:
                    log_status("warning", f"{title} এ ক্লিক করার সময় সমস্যা হয়েছে: {str(click_err)}")

                # লিসেনার রিমুভ করা যাতে পরের চ্যানেলে জগাখিচুড়ি না পাক
                page.remove_listener("request", handle_request)

                if captured_m3u8:
                    # তালিকার প্রথম কার্যকর .m3u8 লিংকটি নেওয়া
                    stream_url = captured_m3u8[0]
                    log_status("success", f"[{title}] ডাইনামিক টোকেনযুক্ত m3u8 লিংক পাওয়া গেছে!")
                else:
                    stream_url = ""
                    log_status("warning", f"[{title}] লিংক ক্যাপচার করা সম্ভব হয়নি।")

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })

            # চূড়ান্ত .m3u প্লেলিস্ট ফাইল তৈরি করা
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in extracted_channels:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                    f.write(f'{ch["url"]}\n')

            log_status("success", f"প্লেলিস্ট সফলভাবে তৈরি হয়েছে! মোট কার্যকরী চ্যানেল: {len(extracted_channels)}")

        except Exception as e:
            log_status("error", f"ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("info", "প্রসেস শেষ হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
