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
        f.write("--- PlusBox TV 100% Working Direct Iframe Extraction Log ---\n\n")

    log_status("info", "চূড়ান্ত ও ১০০% কার্যকরী স্ক্রিপ্ট শুরু হয়েছে...")

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

                stream_url = ""
                try:
                    # ১. থাম্বনেইলে সরাসরি ক্লিক করা (যা ওয়েবসাইটটির নিজের startChannel ফাংশন ট্রিগার করবে)
                    link.scroll_into_view_if_needed()
                    link.click()
                    
                    # ২. টোকেন জেনারেট হয়ে আইফ্রেমের ভেতরে সোর্স বসানোর জন্য ৩ সেকেন্ড অপেক্ষা
                    time.sleep(3)

                    # ৩. সরাসরি আইফ্রেমের 'src' অ্যাট্রিবিউট রিড করা (যেখানে ১০০% জেনুইন টোকেনসহ লিংক থাকে)
                    iframe = page.query_selector("iframe#player")
                    if iframe:
                        iframe_src = iframe.get_attribute("src")
                        if iframe_src and "token=" in iframe_src:
                            stream_url = iframe_src
                            log_status("success", f"[{title}] টোকেনসহ পারফেক্ট লিংক পাওয়া গেছে!")
                        else:
                            # যদি আইফ্রেমের সোর্স সরাসরি না মিলে, তবে data-source থেকে টোকেন বা বেস লিংক নেওয়া
                            data_source = link.get_attribute("data-source")
                            if data_source:
                                stream_url = data_source
                                log_status("warning", f"[{title}] আইফ্রেম থেকে টোকেন মেলেনি, ডেটা-সোর্স ব্যবহার করা হয়েছে।")
                    
                except Exception as e:
                    log_status("warning", f"[{title}] প্রসেস করতে গিয়ে সমস্যা: {str(e)}")

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
