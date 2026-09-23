import os
import time
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"

channels_data = {}

def log_status(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def scrape_channels():
    # স্ট্যাটাস ফাইল রিসেট করা
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Scraper Log ---\n")

    log_status("스크립্ট শুরু হয়েছে (Script started)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # নেটওয়ার্ক রিকোয়েস্ট ট্র্যাক করার জন্য (m3u8 বা স্ট্রিম লিংক ধরার জন্য)
        def handle_request(request):
            if ".m3u8" in request.url:
                log_status(f"m3u8 লিংক পাওয়া গেছে: {request.url}")

        page.on("request", handle_request)

        try:
            log_status(f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # কিছু সময় অপেক্ষা করা যাতে স্লাইডার এবং জাভাস্ক্রিপ্ট পুরোপুরি লোড হয়
            time.sleep(5)

            log_status("স্লাইডার থেকে চ্যানেল ডেটা এক্সট্রাক্ট করা হচ্ছে...")

            # হরিজন্টাল স্লাইডারের চ্যানেল আইটেমগুলো খোঁজা (DOM স্ট্রাকচার অনুযায়ী সিলেক্টর অ্যাডজাস্ট করা হতে পারে)
            # সাধারণত এই সাইটগুলোতে ইমেজ ট্যাগ ও টাইটেল থাকে
            for i in range(10): # যদি অনেক চ্যানেল থাকে তবে স্লাইডার কয়েকবার ক্লিক করার লজিক
                channel_elements = page.query_selector_all(".channel-item, .swiper-slide, img") # উদাহরণ সিলেক্টর
                
                # স্লাইডারের নেক্সট বাটনে ক্লিক করার কোড (যদি থাকে)
                next_btn = page.query_selector(".next-arrow, .swiper-button-next")
                if next_btn:
                    try:
                        next_btn.click()
                        time.sleep(1)
                    except:
                        break
                else:
                    break

            # DOM থেকে চ্যানেল টাইটেল ও লোগো সংগ্রহ করার লজিক
            # (আপনার ব্রাউজারের ইন্সপেক্ট এলিমেন্ট করে সঠিক ক্লাস বা ট্যাগ এখানে বসাতে হবে)
            items = page.query_selector_all("img") # সাময়িকভাবে সব ইমেজ টলারেন্সের জন্য
            
            extracted_channels = []
            for item in items:
                src = item.get_attribute("src")
                alt = item.get_attribute("alt")
                if src and alt:
                    extracted_channels.append({
                        "title": alt,
                        "logo": src,
                        "url": "https://example.com/stream.m3u8" # ডাইনামিক লিংক হ্যান্ডেল করার জায়গা
                    })

            # প্লেলিস্ট ফাইল রাইট করা
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                if extracted_channels:
                    for ch in extracted_channels:
                        f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                        f.write(f'{ch["url"]}\n')
                    log_status(f"মোট {len(extracted_channels)} টি চ্যানেল সফলভাবে m3u প্লেলিস্টে যুক্ত করা হয়েছে।")
                else:
                    # যদি সরাসরি DOM থেকে না মিলে, অন্তত ডিফল্ট টেমপ্লেট বা নোটিশ রাখা
                    f.write('#EXTINF:-1, PlusBox TV Placeholder\n')
                    f.write('https://plusbox.tv/\n')
                    log_status("সতর্কতা: কোনো চ্যানেল এলিমেন্ট সরাসরি পাওয়া যায়নি, ডিফল্ট এন্ট্রি দেওয়া হয়েছে।")

        except Exception as e:
            log_status(f"ত্রুটি দেখা দিয়েছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("ব্রাউজার বন্ধ করা হয়েছে এবং প্রসেস শেষ।")

if __name__ == "__main__":
    scrape_channels()
