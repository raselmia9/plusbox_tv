import os
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"

def log_status(level, message):
    prefix = {"info": "🔵 [INFO]", "success": "🟢 [SUCCESS]", "error": "🔴 [ERROR]"}.get(level, "⚪ [LOG]")
    log_msg = f"{prefix} {message}"
    print(log_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_msg + "\n")

def scrape_channels():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("--- PlusBox TV Direct Source Extraction Log ---\n\n")

    log_status("info", "সরাসরি সোর্স কোড ভিত্তিক এক্সট্রাকশন শুরু হয়েছে...")

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

            # সোর্স কোডের সেই কাঙ্ক্ষিত থাম্বনেইল এলিমেন্টগুলো সরাসরি সিলেক্ট করা
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

                # লোগো সংগ্রহ করা
                img = link.query_selector("img")
                logo_url = ""
                if img:
                    src = img.get_attribute("src")
                    if src:
                        logo_url = "https://plusbox.tv" + src if src.startswith("/") else src

                stream_url = ""
                if data_source:
                    # সোর্স কোডের লজিক অনুযায়ী embed.html কে সরাসরি index.fmp4.m3u8 এ রূপান্তর করা
                    # যেমন: .../embed.html?mute=false... -> .../index.fmp4.m3u8?mute=false...
                    stream_url = data_source.replace("embed.html", "index.fmp4.m3u8")

                if stream_url and logo_url:
                    extracted_channels.append({
                        "title": title,
                        "logo": logo_url,
                        "url": stream_url
                    })
                    log_status("success", f"[{title}] লিংক সফলভাবে তৈরি হয়েছে।")

            # .m3u প্লেলিস্ট ফাইল তৈরি
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
