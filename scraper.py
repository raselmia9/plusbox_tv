import os
import time
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"

def log_status(level, message):
    prefix = {"info": "🔵 [INFO]", "success": "🟢 [SUCCESS]", "warning": "🟡 [WARNING]", "error": "🔴 [ERROR]"}.get(level, "⚪ [LOG]")
    log_msg = f"{prefix} {message}"
    print(log_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def scrape_channels():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV True Token M3U8 Capture Log ---\n\n")

    log_status("info", "সঠিক টোকেনসহ m3u8 ক্যাপচার স্ক্রিপ্ট শুরু হয়েছে...")

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

            if total_channels == 0:
                log_status("error", "কোনো চ্যানেল এলিমেন্ট পাওয়া যায়নি!")
                return

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

                captured_token_stream = []

                # সুনির্দিষ্ট ফিল্টার: শুধুমাত্র index.fmp4.m3u8 এবং যেটার ভেতরে লম্বা ভ্যালিড টোকেন আছে
                def handle_request(request):
                    req_url = request.url
                    if "index.fmp4.m3u8" in req_url and "token=" in req_url:
                        # টোকেনসহ লিংকটি ছোট হয় না, তাই লেন্থ চেক করা হলো যাতে ফালতু বা খালি লিংক না আসে
                        if len(req_url) > 100 and "token=&" not in req_url and not req_url.endswith("token="):
                            if req_url not in captured_token_stream:
                                captured_token_stream.append(req_url)

                page.on("request", handle_request)

                try:
                    # থাম্বনেইলে ক্লিক করা যাতে জাভাস্ক্রিপ্ট রিয়েল টোকেন জেনারেট করে m3u8 রিকোয়েস্ট পাঠায়
                    link.scroll_into_view_if_needed()
                    link.click()
                    
                    # টোকেন জেনারেট হয়ে নেটওয়ার্কে আসার জন্য ৪ সেকেন্ড অপেক্ষা
                    time.sleep(4.0)
                except Exception as e:
                    log_status("warning", f"[{title}] ক্লিকে সমস্যা: {str(e)}")

                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_token_stream:
                    # একদম সঠিক এবং ভ্যালিড টোকেনযুক্ত শেষ লিংকটি নেওয়া
                    stream_url = captured_token_stream[-1]
                    log_status("success", f"[{title}] সঠিক টোকেনযুক্ত .m3u8 লিংক পাওয়া গেছে!")
                else:
                    log_status("error", f"[{title}] কোনো কার্যকরী টোকেনযুক্ত লিংক পাওয়া যায়নি!")

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })

            # প্লেলিস্ট ফাইল তৈরি (.m3u)
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
