import os
import time
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"

def log_status(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def scrape_channels():
    # স্ট্যাটাস ফাইল শুরু করার আগে আগের ফাইল খালি করে নেওয়া
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Scraper Log ---\n")

    log_status("스크্রিপ্ট শুরু হয়েছে (Script started)...")
    
    channels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            log_status(f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # নেটওয়ার্ক রিকোয়েস্ট বা পেজ এলিমেন্ট থেকে m3u8 ও চ্যানেল ইনফো ট্র্যাক করার লজিক
            # (ওয়েবসাইটের স্ট্রাকচার অনুযায়ী এখানে সিলেক্টর বা ইন্টারসেপ্ট হ্যান্ডেল করতে হবে)
            
            log_status("পেজ সফলভাবে লোড হয়েছে। ডেটা প্রসেস করা হচ্ছে...")
            
            # উদাহরণস্বরূপ ডামি স্ট্রাকচার (আপনার সাইটের এসটিএমএল অনুযায়ী এটি কাস্টমাইজ করতে হবে):
            # elements = page.query_selector_all(".channel-item")
            
            # প্লেলিস্ট লেখার কাজ
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                for ch in channels:
                    f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                    f.write(f'{ch["url"]}\n')
            
            log_status("সফলভাবে m3u প্লেলিস্ট তৈরি করা হয়েছে।")

        except Exception as e:
            log_status(f"ত্রুটি দেখা দিয়েছে: str({e})")
        
        finally:
            browser.close()
            log_status("ব্রাউজার বন্ধ করা হয়েছে এবং প্রসেস শেষ।")

if __name__ == "__main__":
    scrape_channels()
