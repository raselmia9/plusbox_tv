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
    # স্ট্যাটাস ফাইল রিসেট করা (তারিখ ও সময় ছাড়া সুন্দর রঙিন ডট সহ)
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Scraper Status Log ---\n\n")

    log_status("info", "স্ক্রিপ্ট সফলভাবে শুরু হয়েছে...")

    extracted_channels = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        page = context.new_page()

        try:
            log_status("info", f"লিংক ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            page.wait_for_load_state("networkidle")
            
            # স্লাইডার পুরোপুরি লোড হওয়ার জন্য সময় দেওয়া
            time.sleep(5)

            log_status("info", "স্লাইডার থেকে চ্যানেল কার্ড, নাম এবং ডাটা সোর্স খোঁজা হচ্ছে...")

            # HTML স্ট্রাকচার অনুযায়ী প্রতিটি চ্যানেলের <a> ট্যাগগুলো সিলেক্ট করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            
            log_status("debug", f"মোট চ্যানেল ট্যাগ পাওয়া গেছে: {len(channel_links)} টি")

            for link in channel_links:
                # ১. ডেটা সোর্স বা মাস্টার লিংক বের করা (data-source এট্রিবিউট থেকে)
                source_url = link.get_attribute("data-source")
                
                # ২. চ্যানেলের নাম বের করা (href অথবা data-name থেকে)
                href = link.get_attribute("href")
                data_name = link.get_attribute("data-name")
                
                title = ""
                if data_name:
                    title = data_name
                elif href and href.startswith("#"):
                    title = href.replace("#", "").strip()
                
                if not title:
                    title = "Unknown Channel"

                # ৩. লোগো বা ইমেজ লিংক বের করা
                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        if src.startswith("/"):
                            logo_url = "https://plusbox.tv" + src
                        elif not src.startswith("http"):
                            logo_url = "https://plusbox.tv/" + src
                        else:
                            logo_url = src

                # যদি সঠিক সোর্স লিংক এবং লোগো থাকে, তবে লিস্টে যোগ করা
                if source_url and logo_url:
                    # ডুপ্লিকেট চেক
                    if not any(ch['url'] == source_url for ch in extracted_channels):
                        extracted_channels.append({
                            "title": title,
                            "logo": logo_url,
                            "url": source_url
                        })

            log_status("info", f"সফলভাবে প্রসেস করা মোট চ্যানেল: {len(extracted_channels)} টি")

            # প্লেলিস্ট ফাইল তৈরি করা (.m3u)
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                if len(extracted_channels) > 0:
                    for ch in extracted_channels:
                        f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                        f.write(f'{ch["url"]}\n')
                    log_status("success", f"প্লেলিস্ট সফলভাবে তৈরি হয়েছে! মোট চ্যানেল: {len(extracted_channels)}")
                else:
                    f.write('#EXTINF:-1, PlusBox TV No Channel Found\n')
                    f.write('https://plusbox.tv/\n')
                    log_status("warning", "কোনো চ্যানেল বা ডাটা সোর্স পাওয়া যায়নি।")

        except Exception as e:
            log_status("error", f"ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("info", "প্রসেস শেষ হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
