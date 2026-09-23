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
        "error": "🔴 [ERROR]"
    }
    prefix = dots.get(level, "⚪ [LOG]")
    log_msg = f"{prefix} {message}"
    print(log_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def scrape_channels():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Fast Token Capture Log ---\n\n")

    log_status("info", "ফাস্ট টোকেন ক্যাপচার স্ক্রিপ্ট শুরু হয়েছে...")

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

            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            total_channels = len(channel_links)
            log_status("info", f"মোট চ্যানেল পাওয়া গেছে: {total_channels} টি")

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

                captured_stream = []

                # প্রতিবার ক্লিকের সময় রিকোয়েস্ট ইন্টারসেপ্ট করার জন্য লোকাল লিসেনার
                def handle_request(request):
                    req_url = request.url
                    if "index.fmp4.m3u8" in req_url and "token=" in req_url:
                        if req_url not in captured_stream:
                            captured_stream.append(req_url)

                page.on("request", handle_request)

                try:
                    # দ্রুত স্ক্রোল ও ক্লিক
                    link.scroll_into_view_if_needed()
                    link.click()
                    
                    # টোকেন আসার জন্য মাত্র ২.৫ থেকে ৩ সেকেন্ড অপেক্ষা (সময় কমানোর জন্য অপ্টিমাইজড)
                    time.sleep(2.8)
                except Exception as e:
                    log_status("warning", f"[{title}] ক্লিকে সমস্যা: {str(e)}")

                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_stream:
                    # একদম ফ্রেশ টোকেনযুক্ত লিংকটি নেওয়া
                    stream_url = captured_stream[-1]
                    log_status("success", f"[{title}] টোকেনসহ লিংক সফলভাবে ক্যাচ হয়েছে!")
                else:
                    # ফলব্যাক: যদি নেটওয়ার্কে হঠাৎ না ধরে, তবে ডেটা সোর্স থেকে নেওয়া
                    data_source = link.get_attribute("data-source")
                    if data_source:
                        stream_url = data_source
                        log_status("warning", f"[{title}] টোকেন পাওয়া যায়নি, বেস লিংক ব্যবহার করা হয়েছে।")

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

if __name__ == "__main__":
    scrape_channels()
