import requests, json, re, logging
from bs4 import BeautifulSoup
from datetime import datetime, timezone

# === CONFIGURATION ===
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
EVENTS_URL = "https://thedaddy.top/schedule/schedule-generated.php"
CHANNELS_URL = "https://thedaddy.top/24-7-channels.php"
HEADERS = {
    "User-Agent": UA,
    "Referer": "https://jxoplay.xyz/",
    "Origin": "https://jxoplay.xyz",
    "Accept": "*/*",
    "Connection": "close",
    "Icy-MetaData": "1",
    "Etag": "multistreams"
}
SETTINGS = {"time_format": "1"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === UTILS ===
def log(msg):
    try:
        logging.info(f"\n    {msg}" if isinstance(msg, str) else str(msg))
    except Exception as e:
        logging.error(f"[Log Failure] {e}")

def get_local_time(utc_time_str):
    try:
        utc_now = datetime.now(timezone.utc)
        fmt = "%I:%M%p" if any(x in utc_time_str.lower() for x in ["am", "pm"]) else "%H:%M"
        event_time_utc = datetime.strptime(utc_time_str, fmt)
        event_time_utc = event_time_utc.replace(year=utc_now.year, month=utc_now.month, day=utc_now.day, tzinfo=timezone.utc)
        local_time = event_time_utc.astimezone()
        return local_time.strftime("%H:%M") if SETTINGS["time_format"] == "1" else local_time.strftime("%I:%M %p").lstrip("0")
    except Exception as e:
        log(f"Time conversion failed: {e}")
        return utc_time_str

# === LIVE EVENTS MODULE ===
def fetch_live_events():
    try:
        headers = {
            "User-Agent": UA,
            "Referer": "https://thedaddy.top/",
            "Origin": "https://thedaddy.top",
            "Accept": "application/json",
            "Connection": "keep-alive"
        }
        resp = requests.get(EVENTS_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        schedule = resp.json()
        events_by_category = []
        for _, categories in schedule.items():
            for category, events in categories.items():
                events_by_category.append((category, events))
        return events_by_category
    except Exception as e:
        log(f"Failed to fetch live events: {e}")
        return []

def display_event_stream(events_by_category):
    print("\n📚 Available Event Categories:\n")
    for i, (category, _) in enumerate(events_by_category, 1):
        print(f"{i}. {category}")
    try:
        cat_choice = int(input("\nSelect category number: ")) - 1
        if not (0 <= cat_choice < len(events_by_category)):
            print("❌ Invalid category.")
            return
        category, events = events_by_category[cat_choice]
        print(f"\n📅 {category}")
        for i, event in enumerate(events, 1):
            title = event.get("event", "Untitled").strip()
            time = get_local_time(event.get("time", "Unknown"))
            print(f"  {i}. 🕒 {time} — 🎬 {title}")
        evt_choice = int(input("\nSelect event number: ")) - 1
        if not (0 <= evt_choice < len(events)):
            print("❌ Invalid event.")
            return
        selected_event = events[evt_choice]
        channels = selected_event.get("channels", []) + selected_event.get("channels2", [])
        if not channels:
            print("❌ No channels listed.")
            return
        print(f"\n🎬 {selected_event.get('event', 'Untitled')}")
        for i, ch in enumerate(channels, 1):
            print(f"  {i}. 📺 {ch.get('channel_name')} (ID: {ch.get('channel_id')})")
        ch_choice = int(input("\nSelect channel number: ")) - 1
        if not (0 <= ch_choice < len(channels)):
            print("❌ Invalid channel.")
            return
        cid = channels[ch_choice].get("channel_id")
        fetch_m3u8(cid)
    except ValueError:
        print("❌ Invalid input.")

# === LIVE CHANNELS MODULE ===
def fetch_channels(url):
    try:
        response = requests.get(url, headers={"User-Agent": UA}, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        channels, seen_names = [], set()
        start_collecting = False
        for link in soup.find_all("a", href=True):
            name = link.get_text(strip=True)
            href = link["href"]
            if not name or "php" not in href or "18+" in name.lower():
                continue
            if "ABC USA" in name:
                start_collecting = True
            if start_collecting and name.lower() not in seen_names:
                channels.append((name, href))
                seen_names.add(name.lower())
        channels.sort(key=lambda x: x[0].lower())
        return channels
    except Exception as e:
        print(f"\n❌ Failed to fetch channel list: {e}")
        return []

def extract_stream_id(href):
    match = re.search(r"stream-(\d+)\.php", href)
    return match.group(1) if match else None

def fetch_m3u8(stream_id):
    try:
        url = f"https://dad.multistreamz.com/streams/{stream_id}/mono.m3u8"
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        for line in response.text.splitlines():
            if line.strip().startswith("http") and line.strip().endswith(".m3u8"):
                final_url = f"{line.strip()}|User-Agent=Mozilla%2F5.0&Accept=*%2F*&Connection=close&Icy-MetaData=1&Referer=https%3A%2F%2Fjxoplay.xyz%2F&Origin=https%3A%2F%2Fjxoplay.xyz&etag=multistreams"
                print(f"\n🔗 Final Stream URL:\n{final_url}")
                return prompt_continue()
        print("❌ No valid .m3u8 link found.")
    except Exception as e:
        print(f"❌ Failed to fetch .m3u8 for stream-{stream_id}: {e}")

def prompt_continue():
    while True:
        user_input = input("\nEnter 0 to continue or 00 to exit: ").strip()
        if user_input == "0":
            return
        elif user_input == "00":
            print("\n👋 Exiting Daddy Live Stream Gen. See you next time!")
            exit()
        else:
            print("❌ Invalid input. Please enter 0 or 00.")

def display_and_select(channels):
    while True:
        print("\n📺 Available Channels (Deduplicated & Sorted):\n")
        for i, (name, _) in enumerate(channels, 1):
            print(f"{i}. {name}")
        print("0. Back to Main Menu")
        try:
            choice = int(input("\nEnter channel number: "))
            if choice == 0:
                break
            elif 1 <= choice <= len(channels):
                name, url = channels[choice - 1]
                print(f"\n🔗 Selected: {name} → {url}")
                stream_id = extract_stream_id(url)
                if stream_id:
                    fetch_m3u8(stream_id)
                else:
                    print("❌ Could not extract stream ID.")
            else:
                print("❌ Invalid selection.")
        except ValueError:
            print("❌ Please enter a valid number.")

# === MAIN MENU ===
def main_menu():
    while True:
        print("\n🛰️  Daddy Live Stream Gen")
        print("1. Live Events")
        print("2. Live Channels")
        print("3. Exit")
        try:
            choice = int(input("\nSelect an option: "))
            if choice == 1:
                events_by_category = fetch_live_events()
                if events_by_category:
                    display_event_stream(events_by_category)
                else:
                    print("❌ No live events found.")
            elif choice == 2:
                channels = fetch_channels(CHANNELS_URL)
                if channels:
                    display_and_select(channels)
                else:
                    print("❌ No channels found or all were filtered out.")
            elif choice == 3:
                print("\n👋 Exiting Daddy Live Stream Gen. See you next time!")
                break
            else:
                print("❌ Invalid menu option.")
        except ValueError:
            print("❌ Please enter a valid number.")

if __name__ == "__main__":
    main_menu()
