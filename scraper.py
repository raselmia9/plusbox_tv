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
        f.write("--- PlusBox TV Lightning Fast Log ---\n\n")

    log_status("info", "সুপার-ফাস্ট স্ক্রিপ্ট শুরু হয়েছে...")

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

        # নেটওয়ার্ক ইন্টারসেপ্ট করে রিয়েল-টাইম টোকেনযুক্ত মাস্টার লিংকগুলো একটি ডিকশনারিতে ধরে রাখা
        captured_tokens = {}

        def handle_request(request):
            req_url = request.url
            if "index.fmp4.m3u8" in req_url and "token=" in req_url:
                for ch_name in ["GaziTVHD", "SomoyTv", "TSportsHD", "JamunaTV", "IndependentTV", "Channel24", "DBCNews", "EkattorTV", "RTV", "NTV", "ATNNews", "ChannelI", "DeeptoTV", "Maasranga", "DeshTV", "BTVWorld", "BTV", "ATNBangla", "BijoyTV", "AsianTV", "BanglaVision", "Channel9", "EkusheyTv", "MyTV", "StarNews", "News24", "EkhonTV", "ColorsBangla", "IndiaToday", "BloombergTV", "RussiaToday"]:
                    if ch_name.lower() in req_url.lower():
                        captured_tokens[ch_name] = req_url

        page.on("request", handle_request)

        try:
            log_status("info", f"ওয়েবসাইট ভিজিট করা হচ্ছে: {URL}")
            page.goto(URL, timeout=60000)
            
            # সাইট পুরো লোড হওয়ার জন্য একটু সময় দেওয়া এবং ব্যাকএন্ড থেকে টোকেনগুলো নিজে থেকেই ফেচ হতে দেওয়া
            log_status("info", "টোকেন জেনারেট হওয়ার জন্য ১০ সেকেন্ড অপেক্ষা করা হচ্ছে...")
            time.sleep(10)

            # চ্যানেল থাম্বনেইলগুলো থেকে সরাসরি নাম ও লোগো সংগ্রহ করা
            channel_links = page.query_selector_all("a.playignitor.thumbnail")
            total_channels = len(channel_links)
            log_status("info", f"মোট চ্যানেল পাওয়া গেছে: {total_channels} টি")

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

                # ক্যাচ হওয়া টোকেন চেক করা
                stream_url = ""
                for key, val in captured_tokens.items():
                    if key.lower() in title.lower().replace(" ", ""):
                        stream_url = val
                        break

                # যদি সরাসরি নেটওয়ার্কে ক্যাচ না করে, তবে data-source এর সাথে ব্যাকএন্ড রুল অনুযায়ী লিংক তৈরি করা
                if not stream_url:
                    data_source = link.get_attribute("data-source")
                    if data_source:
                        base_backend = data_source.split("/embed.html")[0]
                        stream_url = f"{base_backend}/index.fmp4.m3u8"

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })
                    log_status("success", f"[{title}] লিংক সফলভাবে যোগ করা হয়েছে!")

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
