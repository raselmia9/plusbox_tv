import os
import time
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"

def log_status(level, message):
    # ডেট-টাইমের বদলে কালারফুল ডট/ইমোজি ব্যবহার করা হয়েছে
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
        f.write("--- PlusBox TV Scraper Status Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট সফলভাবে শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        # মোবাইল বা ডেস্কটপ ভিউর জন্য ভিউপোর্ট সেট করা যেতে পারে
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()

        # নেটওয়ার্ক রিকোয়েস্ট মনিটর করার জন্য (m3u8 বা স্ট্রিম লিংক ট্র্যাক করতে)
        def handle_request(request):
            if ".m3u8" in request.url or "stream" in request.url:
                log_status("debug", f"নেটওয়ার্ক রিকোয়েস্ট ট্র্যাক হয়েছে: {request.url}")
        
        page.on("request", handle_request)

        try:
            log_status("info", f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # পেজ পুরোপুরি লোড হওয়ার জন্য কয়েক সেকেন্ড অপেক্ষা
            time.sleep(4)

            log_status("info", "পেজের DOM এবং চ্যানেল এলিমেন্ট খোঁজা হচ্ছে...")

            # স্ক্রিনশট বা পেজ সোর্স থেকে ডিবাগ করার জন্য সমস্ত ইমেজ এলিমেন্ট চেক করা
            images = page.query_selector_all("img")
            log_status("debug", f"পেজে মোট ইমেজ পাওয়া গেছে: {len(images)} টি")

            # হরিজন্টাল স্লাইডার বা চ্যানেল আইটেমগুলোর সঠিক স্ট্রাকচার খুঁজে বের করার চেষ্টা
            # সাধারণত চ্যানেলের লোগো এবং নাম img ট্যাগের src এবং alt বা কাছাকাছি টেক্সটে থাকে
            for index, img in enumerate(images):
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                
                # যদি ইমেজটি কোনো চ্যানেলের লোগো হয় (যেমন লোগো ফোল্ডার বা নির্দিষ্ট সাইজের বা alt নামযুক্ত)
                if src:
                    # যদি alt খালি থাকে, ইমেজ ফাইলের নাম থেকে টাইটেল বের করার চেষ্টা
                    title = alt if alt and alt.strip() != "" else f"Channel {index + 1}"
                    
                    # যদি লিংকটি রিলেটিভ হয় তবে ফুল ইউরল করা
                    if src.startswith("/"):
                        src = "https://plusbox.tv" + src
                    elif not src.startswith("http"):
                        src = "https://plusbox.tv/" + src

                    # ডুপ্লিকেট এন্ট্রি এড়ানোর চেক
                    if not any(ch['logo'] == src for ch in extracted_channels):
                        extracted_channels.append({
                            "title": title,
                            "logo": src,
                            "url": "https://plusbox.tv/" # ডিফল্ট বা ইন্টারসেপ্ট করা স্ট্রিম লিংক
                        })

            log_status("info", f"ফিল্টার করার পর মোট চ্যানেল পাওয়া গেছে: {len(extracted_channels)} টি")

            # প্লেলিস্ট ফাইল তৈরি করা
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                if len(extracted_channels) > 0:
                    for ch in extracted_channels:
                        f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                        f.write(f'{ch["url"]}\n')
                    log_status("success", f"প্লেলিস্ট সফলভাবে তৈরি হয়েছে! মোট চ্যানেল: {len(extracted_channels)}")
                else:
                    # যদি কোনো চ্যানেল না পাওয়া যায়, তবে স্ট্যাটাসে কারণ লগ হবে
                    f.write('#EXTINF:-1, PlusBox TV No Channel Found\n')
                    f.write('https://plusbox.tv/\n')
                    log_status("warning", "কোনো চ্যানেল কার্ড বা লোগো পাওয়া যায়নি। সাইটের স্ট্রাকচার পরিবর্তন হতে পারে বা জাভাস্ক্রিপ্ট রেন্ডারিংয়ের জন্য আরও সময় প্রয়োজন।")

        except Exception as e:
            log_status("error", f"স্ক্রিপ্ট রান করার সময় ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("info", "ব্রাউজার বন্ধ করা হয়েছে এবং প্রসেস শেষ।")

if __name__ == "__main__":
    scrape_channels()
