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
        f.write("--- PlusBox TV Optimized Debug Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট সফলভাবে শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        log_status("info", "Chromium ব্রাউজার লঞ্চ করা হচ্ছে (Headless মোড)...")
        
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
            time.sleep(5)
            log_status("success", "ওয়েবসাইট সফলভাবে লোড হয়েছে।")

            # চ্যানেল থাম্বনেইলগুলো খুঁজে বের করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            total_channels = len(channel_links)
            log_status("info", f"মোট চ্যানেল পাওয়া গেছে: {total_channels} টি")

            if total_channels == 0:
                log_status("error", "কোনো চ্যানেল এলিমেন্ট পাওয়া যায়নি!")
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

                # নেটওয়ার্ক রিকোয়েস্ট ইন্টারসেপ্ট করার উন্নত লজিক
                def handle_request(request):
                    req_url = request.url
                    # আমরা শুধু মূল fmp4.m3u8 বা সঠিক মাস্টার লিংকগুলো খুঁজছি এবং টোকেন থাকতে হবে
                    if "index.fmp4.m3u8" in req_url and "token=" in req_url:
                        if req_url not in captured_streams:
                            captured_streams.append(req_url)
                            log_status("debug", f"সঠিক মাস্টার লিংক ক্যাচড: {req_url[:80]}...")

                page.on("request", handle_request)

                try:
                    # এলিমেন্টে স্ক্রোল করে ক্লিক করা
                    link.scroll_into_view_if_needed()
                    link.click()
                    log_status("info", f"[{title}] থাম্বনেইলে ক্লিক করা হয়েছে। ফ্রেশ টোকেনের জন্য অপেক্ষা করা হচ্ছে...")
                    
                    # গিটহাব অ্যাকশনসের স্লো গতির কথা মাথায় রেখে সময় ৭ সেকেন্ড করা হলো 
                    # যাতে সাইট কোনো ক্যাশড টোকেন না দিয়ে একদম রিয়েল-টাইম ফ্রেশ টোকেন দিতে বাধ্য হয়
                    time.sleep(7)

                except Exception as click_err:
                    log_status("warning", f"[{title}] ক্লিক বা ইন্টারঅ্যাকশনে সমস্যা: {str(click_err)}")

                # লিসেনার রিমুভ করা পরবর্তী চ্যানেলের জন্য
                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_streams:
                    # একদম শেষের বা সর্বশেষ ফ্রেশ লিংকটি পিক করা
                    stream_url = captured_streams[-1]
                    log_status("success", f"[{title}] একদম ফ্রেশ এবং সঠিক স্ট্রিম লিংক পাওয়া গেছে!")
                else:
                    # ফলব্যাক বা ব্যাকআপ হিসেবে অন্য কোনো মডিফাইড লিংক বা data-source চেক করা
                    data_source = link.get_attribute("data-source")
                    if data_source and "token=" in data_source:
                        stream_url = data_source
                        log_status("warning", f"[{title}] নেটওয়ার্কে লাইভ লিংক না পাওয়ায় ডাটা সোর্স ব্যবহার করা হয়েছে।")
                    else:
                        log_status("error", f"[{title}] কোনো কার্যকরী লিংক পাওয়া যায়নি!")

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
            log_status("info", "ব্রাউজার বন্ধ করা হয়েছে। প্রসেস সমাপ্ত।")

if __name__ == "__main__":
    scrape_channels()
