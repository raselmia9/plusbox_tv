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
        f.write("--- PlusBox TV Scraper Status Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট সফলভাবে শুরু হয়েছে...")

    extracted_channels = []
    captured_streams = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()

        # নেটওয়ার্ক রিকোয়েস্ট থেকে সরাসরি m3u8 বা স্ট্রিম লিংক ট্র্যাক করার জন্য
        def handle_request(request):
            req_url = request.url
            if ".m3u8" in req_url or "stream" in req_url or "playlist" in req_url:
                if req_url not in captured_streams:
                    captured_streams.add(req_url)
                    log_status("debug", f"নেটওয়ার্ক স্ট্রিম লিংক পাওয়া গেছে: {req_url}")

        page.on("request", handle_request)

        try:
            log_status("info", f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            time.sleep(5)  # পেজ ও স্লাইডার পুরোপুরি লোড হওয়ার সময় দেওয়া

            log_status("info", "চ্যানেল কার্ড, টাইটেল এবং লোগো এক্সট্রাক্ট করা হচ্ছে...")

            # স্লাইডার বা চ্যানেল আইটেমগুলোর সম্ভাব্য কন্টেইনার বা কার্ড খোঁজা
            # সাধারণত <a>, <div> অথবা <li> ট্যাগের ভেতরে ইমেজ এবং টেক্সট থাকে
            channel_cards = page.query_selector_all("a, .channel-item, .swiper-slide, div")
            
            for card in channel_cards:
                img = card.query_selector("img")
                if img:
                    src = img.get_attribute("src")
                    alt = img.get_attribute("alt")
                    
                    # যদি লোগো বা src পাওয়া যায়
                    if src:
                        if src.startswith("/"):
                            logo_url = "https://plusbox.tv" + src
                        elif not src.startswith("http"):
                            logo_url = "https://plusbox.tv/" + src
                        else:
                            logo_url = src

                        # চ্যানেলের নাম খোঁজা (alt থেকে অথবা কার্ডের ভেতরের টেক্সট থেকে)
                        title = ""
                        if alt and alt.strip() != "":
                            title = alt.strip()
                        else:
                            card_text = card.inner_text().strip()
                            if card_text and len(card_text) < 50:
                                title = card_text.split('\n')[0]
                        
                        if not title:
                            title = "Unknown Channel"

                        # চ্যানেলের নিজস্ব লিংক বা স্ট্রিম লিংক খোঁজা (যদি অ্যাট্রিবিউটে থাকে)
                        href = card.get_attribute("href")
                        data_link = card.get_attribute("data-url") or card.get_attribute("data-stream")
                        
                        stream_url = "https://plusbox.tv/"  # ডিফল্ বা ফলব্যাক লিংক
                        if data_link:
                            stream_url = data_link
                        elif href and href != "#" and "http" in href:
                            stream_url = href

                        # ডুপ্লিকেট এড়াতে লিস্টে যোগ করা
                        if not any(ch['logo'] == logo_url for ch in extracted_channels):
                            extracted_channels.append({
                                "title": title,
                                "logo": logo_url,
                                "url": stream_url
                            })

            log_status("info", f"মোট ইউনিক চ্যানেল কার্ড পাওয়া গেছে: {len(extracted_channels)} টি")

            # প্লেলিস্ট ফাইল তৈরি করা
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                if len(extracted_channels) > 0:
                    for ch in extracted_channels:
                        # যদি নেটওয়ার্ক থেকে ধরা কোনো স্ট্রিম লিংক থাকে, সেগুলো অ্যাসাইন করা যেতে পারে
                        f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                        f.write(f'{ch["url"]}\n')
                    log_status("success", f"প্লেলিস্ট সফলভাবে আপডেট হয়েছে! মোট চ্যানেল: {len(extracted_channels)}")
                else:
                    f.write('#EXTINF:-1, PlusBox TV No Data\n')
                    f.write('https://plusbox.tv/\n')
                    log_status("warning", "চ্যানেল কার্ড বা নাম পাওয়া যায়নি।")

        except Exception as e:
            log_status("error", f"ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("info", "প্রসেস শেষ হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
