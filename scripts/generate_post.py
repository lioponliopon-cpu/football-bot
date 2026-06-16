"""
Football Schedule Bot - 完整版
自動抓取賽程 → 生成圖片 → 發布到 Instagram
"""
import os
import time
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

# ── 設定區 ──────────────────────────────────────────────
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
IG_ACCESS_TOKEN  = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID       = os.environ.get("IG_USER_ID", "")
IMGBB_API_KEY    = os.environ.get("IMGBB_API_KEY", "")

FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "NotoSansCJK.otf")

BG     = (13,17,23)
CARD   = (22,27,34)
GREEN  = (35,134,54)
WHITE  = (240,246,252)
GRAY   = (139,148,158)
BORDER = (48,54,61)
GOLD   = (240,180,41)

def mock_fixtures():
    return [
        {"date":"06/14","time":"21:00","home":"巴西","away":"阿根廷","score":"VS"},
        {"date":"06/14","time":"00:00","home":"法國","away":"西班牙","score":"VS"},
        {"date":"06/15","time":"18:00","home":"德國","away":"英格蘭","score":"VS"},
        {"date":"06/15","time":"21:00","home":"葡萄牙","away":"荷蘭","score":"VS"},
        {"date":"06/16","time":"03:00","home":"義大利","away":"克羅埃西亞","score":"VS"},
        {"date":"06/16","time":"21:00","home":"日本","away":"韓國","score":"VS"},
    ]

def fetch_fixtures():
    today = datetime.now()
    end   = today + timedelta(days=7)
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params  = {"league":1,"season":2026,"from":today.strftime("%Y-%m-%d"),"to":end.strftime("%Y-%m-%d"),"timezone":"Asia/Taipei"}
    res = requests.get(url, headers=headers, params=params, timeout=10)
    fixtures = []
    for f in res.json().get("response", []):
        utc_time = datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00"))
        tw_time  = utc_time + timedelta(hours=8)
        fixtures.append({"date":tw_time.strftime("%m/%d"),"time":tw_time.strftime("%H:%M"),
                         "home":f["teams"]["home"]["name"],"away":f["teams"]["away"]["name"],"score":"VS"})
    return fixtures[:6]

def generate_image(fixtures, path="output/schedule.png"):
    W, H = 1080, 1350
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    def font(size):
        if os.path.exists(FONT_PATH):
            return ImageFont.truetype(FONT_PATH, size)
        return ImageFont.load_default()

    draw.rectangle([0, 0, W, 8], fill=GREEN)
    draw.text((W//2, 70),  "⚽ 本週足球賽程", font=font(52), fill=WHITE, anchor="mm")
    draw.text((W//2, 125), f"台灣時間 · {datetime.now().strftime('%Y.%m.%d')} 更新", font=font(26), fill=GRAY, anchor="mm")
    draw.rectangle([60, 155, W-60, 158], fill=BORDER)

    card_h, card_gap = 150, 12
    for i, f in enumerate(fixtures):
        y = 170 + i * (card_h + card_gap)
        draw.rounded_rectangle([50, y, W-50, y+card_h], radius=16, fill=CARD, outline=BORDER, width=1)
        draw.rounded_rectangle([50, y, 180, y+card_h],  radius=16, fill=GREEN)
        draw.rectangle([150, y, 180, y+card_h], fill=GREEN)
        draw.text((115, y+38),  f["date"], font=font(22), fill=WHITE, anchor="mm")
        draw.text((115, y+75),  f["time"], font=font(28), fill=WHITE, anchor="mm")
        draw.text((115, y+110), "台灣時間", font=font(17), fill=(200,255,200), anchor="mm")
        draw.text((310,   y+75), f["home"],  font=font(30), fill=WHITE, anchor="mm")
        draw.text((W//2,  y+75), f["score"], font=font(30), fill=GOLD,  anchor="mm")
        draw.text((W-310, y+75), f["away"],  font=font(30), fill=WHITE, anchor="mm")

    draw.rectangle([60, H-110, W-60, H-109], fill=BORDER)
    draw.text((W//2, H-75), "追蹤帳號 不漏球 ⚽",    font=font(30), fill=GREEN, anchor="mm")
    draw.text((W//2, H-38), "@your_football_account", font=font(22), fill=GRAY,  anchor="mm")
    draw.rectangle([0, H-8, W, H], fill=GREEN)

    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, quality=95)
    print(f"✅ 圖片已生成：{path}")
    return path

def upload_image(path):
    import base64
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    res = requests.post("https://api.imgbb.com/1/upload", data={"key":IMGBB_API_KEY,"image":b64}, timeout=30)
    url = res.json()["data"]["url"]
    print(f"✅ 圖片已上傳：{url}")
    return url

def post_to_instagram(image_url, caption):
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={"image_url":image_url,"caption":caption,"access_token":IG_ACCESS_TOKEN}, timeout=15)
    print(f"建立媒體：{res.json()}")
    container_id = res.json().get("id")
    if not container_id:
        print("❌ 建立媒體失敗")
        return
    print("⏳ 等待 30 秒...")
    time.sleep(30)
    res = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
        data={"creation_id":container_id,"access_token":IG_ACCESS_TOKEN}, timeout=15)
    print(f"發布結果：{res.json()}")
    if res.json().get("id"):
        print("✅ 發布成功！")
    else:
        print("❌ 發布失敗")

def make_caption(fixtures):
    lines = ["⚽ 本週足球賽程（台灣時間）\n"]
    for f in fixtures:
        lines.append(f"📅 {f['date']} {f['time']}")
        lines.append(f"   {f['home']} vs {f['away']}\n")
    lines += ["━━━━━━━━━━━━━━━","🔔 追蹤帳號，開賽前自動通知！","","#世界盃 #足球 #賽程 #WorldCup2026 #football"]
    return "\n".join(lines)

def main():
    print("🤖 Football Bot 啟動中...")
    print(f"字體存在：{os.path.exists(FONT_PATH)}")
    fixtures = fetch_fixtures() if API_FOOTBALL_KEY else mock_fixtures()
    img_path = generate_image(fixtures)
    if IG_ACCESS_TOKEN and IMGBB_API_KEY:
        image_url = upload_image(img_path)
        post_to_instagram(image_url, make_caption(fixtures))
    else:
        print("⚠️ 未設定 Token，跳過發布")
    print("✅ 完成！")

if __name__ == "__main__":
    main()
