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
        f.write("--- PlusBox TV Direct .m3u8 Token Capture Log ---\n\n")

    log_status("info", "সঠিক .m3u8 ও টোকেন ক্যাপচার স্ক্রিপ্ট শুরু হয়েছে...")

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
                log_status("error", "কোনো চ্যানেল পাওয়া যায়নি!")
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

                captured_m3u8 = []

                # নেটওয়ার্ক ইন্টারসেপ্ট করার ফাংশন যা শুধু m3u8 এবং token খুঁজবে
                def handle_request(request):
                    req_url = request.url
                    # আমরা সুনির্দিষ্টভাবে fmp4 বা m3u8 এবং টোকেনযুক্ত রিকোয়েস্ট খুঁজছি
                    if ("m3u8" in req_url or "fmp4" in req_url) and "token=" in req_url:
                        if req_url not in captured_m3u8:
                            captured_m3u8.append(req_url)

                page.on("request", handle_request)

                try:
                    # থাম্বনেইলে ক্লিক করা যাতে প্লেয়ার টোকেনসহ m3u8 রিকোয়েস্ট পাঠায়
                    link.scroll_into_view_if_needed()
                    link.click()
                    
                    # টোকেন জেনারেট হয়ে m3u8 রিকোয়েস্ট আসার জন্য ৩.৫ সেকেন্ড অপেক্ষা
                    time.sleep(3.5)
                except Exception as e:
                    log_status("warning", f"[{title}] ক্লিকে সমস্যা: {str(e)}")

                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_m3u8:
                    # একদম শেষের ফ্রেশ .m3u8 লিংকটি পিক করা
                    stream_url = captured_m3u8[-1]
                    log_status("success", f"[{title}] সঠিক .m3u8 ও টোকেন লিংক পাওয়া গেছে!")
                else:
                    log_status("warning", f"[{title}] নেটওয়ার্কে .m3u8 লিংক পাওয়া যায়নি।")

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
