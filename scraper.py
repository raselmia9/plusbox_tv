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
    # স্ট্যাটাস ফাইল রিসেট করা
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Final Production Script Log ---\n\n")

    log_status("info", "চূড়ান্ত স্ক্রিপ্ট কার্যক্রম শুরু করেছে...")

    extracted_channels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", 
                "--disable-setuid-sandbox", 
                "--disable-dev-shm-usage",
                "--disable-accelerated-2d-canvas",
                "--disable-gpu"
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        try:
            log_status("info", f"ওয়েবসাইট ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            time.sleep(3)

            # সব চ্যানেল থাম্বনেইল সিলেক্ট করা
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
                
                # চ্যানেলের নাম নির্ধারণ
                title = data_name if data_name else (href.replace("#", "").strip() if href else f"Channel {index+1}")
                
                # চ্যানেলের লোগো বের করা
                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        logo_url = "https://plusbox.tv" + src if src.startswith("/") else src

                log_status("info", f"[{index+1}/{total_channels}] প্রসেস হচ্ছে: {title}")

                captured_stream = []

                # নেটওয়ার্ক ইন্টারসেপ্ট করার সুনির্দিষ্ট লজিক
                def handle_request(request):
                    req_url = request.url
                    # নিশ্চিত করা হচ্ছে যেন শুধু এই চ্যানেলেরই মাস্টার স্ট্রিম এবং ভ্যালিড টোকেন ধরা পড়ে
                    if "index.fmp4.m3u8" in req_url and "token=" in req_url:
                        # অতিরিক্ত বা ছোট সাব-লিংক বাদ দিয়ে আসল বড় লিংকটি নেওয়া
                        if len(req_url) > 80:
                            if req_url not in captured_stream:
                                captured_stream.append(req_url)

                page.on("request", handle_request)

                try:
                    # এলিমেন্টে স্ক্রোল করে ক্লিক করা (যা ওয়েবসাইটটির নিজস্ব startChannel ফাংশন ট্রিগার করবে)
                    link.scroll_into_view_if_needed()
                    link.click()
                    
                    # টোকেন জেনারেট হয়ে রিকোয়েস্ট আসার জন্য ৩.৫ সেকেন্ড অপেক্ষা
                    time.sleep(3.5)
                except Exception as click_err:
                    log_status("warning", f"[{title}] ক্লিকে সমস্যা: {str(click_err)}")

                # পরবর্তী চ্যানেলের জন্য লিসেনার রিমুভ করা
                page.remove_listener("request", handle_request)

                stream_url = ""
                if captured_stream:
                    # একদম শেষের ফ্রেশ লিংকটি সিলেক্ট করা
                    stream_url = captured_stream[-1]
                else:
                    # ফলব্যাক: যদি নেটওয়ার্কে ডাইরেক্ট না ধরে, তবে ডেটা-সোর্স থেকে টোকেন বা বেস পাথ সাজিয়ে নেওয়া
                    if data_source:
                        stream_url = data_source.replace("/embed.html", "/index.fmp4.m3u8")
                        log_status("warning", f"[{title}] নেটওয়ার্ক থেকে না পাওয়ায় ডেটা-সোর্স ফলব্যাক ব্যবহার করা হয়েছে।")

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })
                    log_status("success", f"[{title}] সফলভাবে যুক্ত হয়েছে।")
                else:
                    log_status("error", f"[{title}] লিংক সংগ্রহ করা সম্ভব হয়নি।")

            # চূড়ান্ত .m3u প্লেলিস্ট ফাইল তৈরি
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
            log_status("info", "ব্রাউজার সফলভাবে বন্ধ করা হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
