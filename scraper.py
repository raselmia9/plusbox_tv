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
        f.write("--- PlusBox TV Direct Source Extraction Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            log_status("info", f"ওয়েবসাইট ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # চ্যানেল থাম্বনেইলগুলো খুঁজে বের করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            total_channels = len(channel_links)
            log_status("info", f"মোট চ্যানেল পাওয়া গেছে: {total_channels} টি")

            if total_channels == 0:
                log_status("error", "কোনো চ্যানেল এলিমেন্ট পাওয়া যায়নি!")
                return

            for index, link in enumerate(channel_links):
                data_name = link.get_attribute("data-name")
                data_source = link.get_attribute("data-source")
                href = link.get_attribute("href")
                title = data_name if data_name else (href.replace("#", "").strip() if href else f"Channel {index+1}")

                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        logo_url = "https://plusbox.tv" + src if src.startswith("/") else src

                log_status("info", f"--- [{index+1}/{total_channels}] প্রসেস করা হচ্ছে: {title} ---")

                stream_url = ""
                if data_source:
                    # সোর্স কোডের লজিক অনুযায়ী embed লিংক থেকে মূল স্ট্রিম পাথ তৈরি করা
                    # যেমন: https://backend.plusbox.tv/GaziTVHD/embed.html?... -> index.fmp4.m3u8 তে রূপান্তর
                    base_backend = data_source.split("/embed.html")[0]
                    
                    # টোকেন এক্সট্রैक्ट করার জন্য ব্রাউজারে ক্লিক করে আইফ্রেম বা নেটওয়ার্ক থেকে টোকেন নেওয়া
                    captured_token = []
                    
                    def handle_request(request):
                        if "token=" in request.url and "GaziTVHD" in request.url or "index.fmp4.m3u8" in request.url:
                            if request.url not in captured_token:
                                captured_token.append(request.url)

                    page.on("request", handle_request)

                    try:
                        link.scroll_into_view_if_needed()
                        link.click()
                        time.sleep(5) # টোকেন লোড হওয়ার জন্য অপেক্ষা
                    except Exception as e:
                        log_status("warning", f"ক্লিকে সমস্যা: {str(e)}")

                    page.remove_listener("request", handle_request)

                    if captured_token:
                        # সঠিক m3u8 লিংকটি ফিল্টার করা
                        m3u8_links = [l for l in captured_token if "index.fmp4.m3u8" in l]
                        stream_url = m3u8_links[0] if m3u8_links else captured_token[0]
                    else:
                        # যদি নেটওয়ার্কে ক্যাচ না করে, তবে সোর্সের বেস পাথ দিয়ে ডিফল্ট স্ট্রিম লিংক বানিয়ে নেওয়া
                        # (যেহেতু ব্যাকএন্ড স্ট্রিম ফরম্যাট নির্দিষ্ট থাকে)
                        token_part = data_source.split("token=")[1] if "token=" in data_source else ""
                        stream_url = f"{base_backend}/index.fmp4.m3u8?token={token_part}"

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })
                    log_status("success", f"[{title}] লিংক সফলভাবে সংগ্রহ করা হয়েছে!")

            # প্লেলিস্ট ফাইল তৈরি
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in extracted_channels:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                    f.write(f'{ch["url"]}\n')

            log_status("success", f"প্লেলিস্ট সফলভাবে তৈরি হয়েছে! মোট চ্যানেল: {len(extracted_channels)}")

        except Exception as e:
            log_status("error", f"বড় ধরনের ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()

if __name__ == "__main__":
    scrape_channels()
