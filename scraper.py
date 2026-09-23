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
        f.write("--- PlusBox TV Deep-Capture Log ---\n\n")

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

                captured_streams = []

                # আরও প্রশস্ত পরিসরে রিকোয়েস্ট ফিল্টার করা (m3u8, mpd, stream, playlist ইত্যাদি)
                def handle_request(request):
                    req_url = request.url
                    if any(ext in req_url for ext in [".m3u8", ".mpd", "playlist", "manifest", "chunk.list"]):
                        if "plusbox.tv" in req_url or "backend" in req_url:
                            if req_url not in captured_streams:
                                captured_streams.append(req_url)

                page.on("request", handle_request)

                try:
                    link.click()
                    # স্ট্রিম রিকোয়েস্ট লোড হওয়ার জন্য একটু বেশি সময় দেওয়া (৪ সেকেন্ড)
                    time.sleep(4)
                except Exception as click_err:
                    log_status("warning", f"{title} এ ক্লিক করার সময় সমস্যা হয়েছে: {str(click_err)}")

                page.remove_listener("request", handle_request)

                # যদি রিয়েল স্ট্রিম লিংক পাওয়া যায় সেটি বসবে, না পেলে ডেটা সোর্স বা ফলব্যাক লিংক বসবে
                if captured_streams:
                    stream_url = captured_streams[0]
                    log_status("success", f"[{title}] রিয়েল স্ট্রিম লিংক পাওয়া গেছে!")
                else:
                    # যদি নেটওয়ার্কে না ধরে, তবে এলিমেন্টের নিজস্ব data-source ব্যাকআপ হিসেবে ব্যবহার করা
                    source_attr = link.get_attribute("data-source")
                    stream_url = source_attr if source_attr else "https://plusbox.tv/"
                    log_status("warning", f"[{title}] স্ট্রিম লিংক না পাওয়ায় ব্যাকআপ সোর্স ব্যবহার করা হয়েছে।")

                if logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })

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
