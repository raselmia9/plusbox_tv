import os
import time
from playwright.sync_api import sync_playwright

URL = "https://plusbox.tv/"
M3U_FILE = "playlist.m3u"
LOG_FILE = "status.txt"
HTML_OUTPUT_FILE = "source_code.html"

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

def format_channel_name(filename):
    name = filename.split('/')[-1].split('.')[0]
    name_mapping = {
        "btvworld": "BTV World", "btv": "BTV", "atnbangla": "ATN Bangla",
        "atnnews": "ATN News", "bijoytv": "Bijoy TV", "asiantv": "Asian TV",
        "banglavision": "Banglavision", "channel24": "Channel 24", "channeli": "Channel i",
        "dbcnews": "DBC News", "channel9": "Channel 9", "deeptotv": "Deepto TV",
        "deshtv": "Desh TV", "ekattortv": "Ekattor TV", "ekusheytv": "Ekushey TV",
        "tsports": "T Sports", "independent": "Independent TV", "gtv": "GTV",
        "jamunatv": "Jamuna TV", "maasranga": "Maasranga TV", "mytv": "My TV",
        "starnews": "Star News", "news24": "News24", "ntv": "NTV", "rtv": "RTV",
        "somoytv": "Somoy TV", "ekhontv": "Ekhon TV", "colorsbangla": "Colors Bangla",
        "indiatoday": "India Today", "bloomberg": "Bloomberg", "russiatoday": "Russia Today",
        "redbulltv": "Red Bull TV", "aljazeera": "Al Jazeera", "enterr10": "Enterr10",
        "discoveryhdworld": "Discovery HD World", "animalplanet": "Animal Planet",
        "ptvsports": "PTV Sports", "sonytv": "Sony TV", "sonyaath": "Sony Aath",
        "sonymaxhd": "Sony Max HD", "ten1": "Ten Sports 1", "ten2": "Ten Sports 2",
        "ten3": "Ten Sports 3", "starsports1hd": "Star Sports 1 HD", "starsports2hd": "Star Sports 2 HD",
        "starsportsselect1": "Star Sports Select 1", "starsportsselect2": "Star Sports Select 2",
        "eurosport": "Eurosport", "btsportsespn": "BT Sport ESPN", "starjalshahd": "Star Jalsha HD",
        "stargoldhd": "Star Gold HD", "zeebanglahd": "Zee Bangla HD", "zeecinemahd": "Zee Cinema HD"
    }
    return name_mapping.get(name, name.replace('-', ' ').title())

def scrape_channels():
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
            
            # স্লাইডার এবং জাভাস্ক্রিপ্ট পুরোপুরি রেন্ডার হওয়ার জন্য সময় দেওয়া
            time.sleep(6)

            # পেজের সম্পূর্ণ রেন্ডার হওয়া HTML সোর্স কোড ফাইল আকারে সেভ করা
            page_content = page.content()
            with open(HTML_OUTPUT_FILE, "w", encoding="utf-8") as html_f:
                html_f.write(page_content)
            log_status("success", f"সম্পূর্ণ সোর্স কোড সফলভাবে {HTML_OUTPUT_FILE} ফাইলে সেভ করা হয়েছে!")

            log_status("info", "চ্যানেল লোগো প্রসেস করা হচ্ছে...")
            images = page.query_selector_all("img")
            
            for img in images:
                src = img.get_attribute("src")
                if src and "channels/" in src:
                    if src.startswith("/"):
                        logo_url = "https://plusbox.tv" + src
                    elif not src.startswith("http"):
                        logo_url = "https://plusbox.tv/" + src
                    else:
                        logo_url = src

                    title = format_channel_name(src)
                    stream_url = "https://plusbox.tv/" # পরবর্তীতে মাস্টার লিংক বসবে

                    if not any(ch['logo'] == logo_url for ch in extracted_channels):
                        if "logo.png" not in logo_url and "appdownload" not in logo_url:
                            extracted_channels.append({
                                "title": title,
                                "logo": logo_url,
                                "url": stream_url
                            })

            # প্লেলিস্ট ফাইল তৈরি
            with open(M3U_FILE, "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")
                if len(extracted_channels) > 0:
                    for ch in extracted_channels:
                        f.write(f'#EXTINF:-1 tvg-logo="{ch["logo"]}" ,{ch["title"]}\n')
                        f.write(f'{ch["url"]}\n')
                    log_status("success", f"প্লেলিস্ট তৈরি হয়েছে! মোট চ্যানেল: {len(extracted_channels)}")
                else:
                    f.write('#EXTINF:-1, PlusBox TV No Channel Found\n')
                    f.write('https://plusbox.tv/\n')
                    log_status("warning", "কোনো চ্যানেল পাওয়া যায়নি।")

        except Exception as e:
            log_status("error", f"ত্রুটি ঘটেছে: {str(e)}")
        
        finally:
            browser.close()
            log_status("info", "প্রসেস শেষ হয়েছে।")

if __name__ == "__main__":
    scrape_channels()
