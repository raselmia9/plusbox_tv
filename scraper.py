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
        f.write("--- PlusBox TV Ultimate Stream Capture Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট শুরু হয়েছে...")
    extracted_channels = []

    with sync_playwright() as p:
        # আমরা ব্রাউজার দৃশ্যমান (headless=False) রাখতে পারি যাতে আপনি দেখতে পান কোথায় ক্লিক হচ্ছে
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            log_status("info", f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # সব চ্যানেল থাম্বনেইলগুলো খুঁজে বের করা
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

                # নেটওয়ার্ক ট্রাফিক ট্র্যাক করার ফাংশন (এক্সটেনশন যেভাবে ধরে)
                def handle_request(request):
                    req_url = request.url
                    # m3u8, fmp4 অথবা টোকেনযুক্ত যেকোনো মিডিয়া স্ট্রিম রিকোয়েস্ট পেলে তা সেভ করবে
                    if ("m3u8" in req_url or "fmp4" in req_url or "preview.mp4" in req_url) and "token=" in req_url:
                        if req_url not in captured_streams:
                            captured_streams.append(req_url)

                page.on("request", handle_request)

                try:
                    log_status("info", f"[{title}] চ্যানেলে ক্লিক করা হচ্ছে...")
                    # নিখুঁতভাবে ক্লিক করার জন্য স্ক্রল করে এলিমেন্টে যাওয়া এবং ক্লিক করা
                    link.scroll_into_view_if_needed()
                    link.click()
                    
                    # ভিডিও প্লেয়ারের iframe লোড হয়ে টোকেনসহ রিকোয়েস্ট সার্ভারে হিট করার জন্য ৪ সেকেন্ড সময় দেওয়া
                    time.sleep(4)

                    # অনেক সময় মূল পেজ ছাড়াও iframe এর ভেতরে রিকোয়েস্ট যায়, তাই আইফ্রেম চেক করা
                    frames = page.frames
                    for frame in frames:
                        if "backend.plusbox.tv" in frame.url:
                            log_status("debug", f"[{title}] আইফ্রেম ফেম পাওয়া গেছে: {frame.url}")

                except Exception as click_err:
                    log_status("warning", f"[{title}] ক্লিক করার সময় সমস্যা: {str(click_err)}")

                # লিসেনার রিমুভ করা যাতে আগের চ্যানেলের ডাটা পরেরটিতে না যায়
                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_streams:
                    # অগ্রাধিকার দেওয়া হবে .m3u8 লিংকটিকে, না পেলে preview.mp4 নেওয়া হবে
                    m3u8_list = [s for s in captured_streams if "m3u8" in s]
                    if m3u8_list:
                        stream_url = m3u8_list[0]
                    else:
                        stream_url = captured_streams[0]
                    
                    log_status("success", f"[{title}] সফলভাবে লিংক পাওয়া গেছে: {stream_url}")
                else:
                    log_status("warning", f"[{title}] কোনো স্ট্রিম লিংক ক্যাপচার করা যায়নি।")

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })

            # চূড়ান্ত .m3u প্লেলিস্ট তৈরি করা
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
            log_status("info", "প্রসেস শেষ হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
