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
        f.write("--- PlusBox TV Detailed Debug Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট সফলভাবে শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        log_status("info", "Chromium ব্রাউজার লঞ্চ করা হচ্ছে (Headless মোড)...")
        
        # গিটহাব অ্যাকশনসের জন্য প্রয়োজনীয় আর্গুমেন্টসহ ব্রাউজার লঞ্চ
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
            log_status("success", "ওয়েবসাইট সফলভাবে লোড হয়েছে।")

            # চ্যানেল থাম্বনেইলগুলো খুঁজে বের করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            total_channels = len(channel_links)
            log_status("info", f"মোট চ্যানেল পাওয়া গেছে: {total_channels} টি")

            if total_channels == 0:
                log_status("error", "কোনো চ্যানেল এলিমেন্ট পাওয়া যায়নি! সিলেক্টর পরিবর্তন হতে পারে।")
                return

            for index, link in enumerate(channel_links):
                data_name = link.get_attribute("data-name")
                href = link.get_attribute("href")
                title = data_name if data_name else (href.replace("#", "").strip() if href else f"Channel {index+1}")

                log_status("info", f"--- [{index+1}/{total_channels}] প্রসেস করা হচ্ছে: {title} ---")

                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        logo_url = "https://plusbox.tv" + src if src.startswith("/") else src

                captured_streams = []

                # নেটওয়ার্ক রিকোয়েস্ট ইন্টারসেপ্ট করার লজিক
                def handle_request(request):
                    req_url = request.url
                    if ("m3u8" in req_url or "fmp4" in req_url or "preview.mp4" in req_url) and "token=" in req_url:
                        if req_url not in captured_streams:
                            captured_streams.append(req_url)
                            log_status("debug", f"ক্যাপচারড লিংক: {req_url[:80]}...")

                page.on("request", handle_request)

                try:
                    # এলিমেন্টে স্ক্রোল করে ক্লিক করা
                    link.scroll_into_view_if_needed()
                    link.click()
                    log_status("info", f"[{title}] থাম্বনেইলে সফলভাবে ক্লিক করা হয়েছে।")
                    
                    # ভিডিও প্লেয়ার রেন্ডার ও টোকেন জেনারেট হওয়ার জন্য সময় দেওয়া
                    time.sleep(4)

                    # আইফ্রেম চেক করা
                    iframe_element = page.query_selector("#player")
                    if iframe_element:
                        log_status("debug", f"[{title}] প্লেয়ার আইফ্রেম পাওয়া গেছে।")
                    else:
                        log_status("warning", f"[{title}] প্লেয়ার আইফ্রেম খুঁজে পাওয়া যায়নি।")

                except Exception as click_err:
                    log_status("warning", f"[{title}] ক্লিক বা ইন্টারঅ্যাকশনে সমস্যা: {str(click_err)}")

                # লিসেনার রিমুভ করা
                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_streams:
                    m3u8_list = [s for s in captured_streams if "m3u8" in s]
                    if m3u8_list:
                        stream_url = m3u8_list[0]
                    else:
                        stream_url = captured_streams[0]
                    
                    log_status("success", f"[{title}] সফলভাবে স্ট্রিম লিংক পাওয়া গেছে!")
                else:
                    # ফলব্যাক হিসেবে data-source ব্যবহার করা যদি নেটওয়ার্কে ক্যাচ না করে
                    data_source = link.get_attribute("data-source")
                    if data_source:
                        stream_url = data_source
                        log_status("warning", f"[{title}] নেটওয়ার্কে লিংক না পাওয়ায় data-source ব্যবহার করা হয়েছে।")
                    else:
                        log_status("error", f"[{title}] কোনো লিংকই পাওয়া যায়নি!")

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })

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
            log_status("info", "ব্রাঊজার বন্ধ করা হয়েছে। প্রসেস সমাপ্ত।")

if __name__ == "__main__":
    scrape_channels()
