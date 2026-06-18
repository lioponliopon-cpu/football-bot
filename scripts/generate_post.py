"""
Football Bot - 完整升級版
支援：本週賽程 / 今日賽程 / 賽後比分 / 積分榜
"""
import os, sys, time, requests, base64
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
IG_ACCESS_TOKEN  = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID       = os.environ.get("IG_USER_ID", "")
IMGBB_API_KEY    = os.environ.get("IMGBB_API_KEY", "")
POST_TYPE        = os.environ.get("POST_TYPE", "weekly")  # weekly / daily / result / standing
LINKTREE_URL     = "https://linktr.ee/your_football_account"  # 改成你的

FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "NotoSansCJK.otf")

BG=(13,17,23); CARD=(22,27,34); GREEN=(35,134,54)
WHITE=(240,246,252); GRAY=(139,148,158); GOLD=(240,180,41); RED=(207,34,46)

def font(size):
    return ImageFont.truetype(FONT_PATH, size) if os.path.exists(FONT_PATH) else ImageFont.load_default()

# ── API ─────────────────────────────────────────────────
def api_get(endpoint, params={}):
    res = requests.get(f"https://v3.football.api-sports.io/{endpoint}",
        headers={"x-apisports-key": API_FOOTBALL_KEY}, params=params, timeout=10)
    return res.json().get("response", [])

def get_fixtures(days_from=0, days_to=7, league=1, season=2026):
    today = datetime.now()
    data  = api_get("fixtures", {
        "league": league, "season": season,
        "from": (today + timedelta(days=days_from)).strftime("%Y-%m-%d"),
        "to":   (today + timedelta(days=days_to)).strftime("%Y-%m-%d"),
        "timezone": "Asia/Taipei"
    })
    out = []
    for f in data:
        t = datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00")) + timedelta(hours=8)
        out.append({
            "date":   t.strftime("%m/%d"),
            "time":   t.strftime("%H:%M"),
            "home":   f["teams"]["home"]["name"],
            "away":   f["teams"]["away"]["name"],
            "home_g": f["goals"]["home"],
            "away_g": f["goals"]["away"],
            "status": f["fixture"]["status"]["short"],
        })
    return out

def mock_fixtures():
    return [
        {"date":"06/14","time":"21:00","home":"巴西","away":"阿根廷","home_g":None,"away_g":None,"status":"NS"},
        {"date":"06/14","time":"00:00","home":"法國","away":"西班牙","home_g":None,"away_g":None,"status":"NS"},
        {"date":"06/15","time":"18:00","home":"德國","away":"英格蘭","home_g":None,"away_g":None,"status":"NS"},
        {"date":"06/15","time":"21:00","home":"葡萄牙","away":"荷蘭","home_g":None,"away_g":None,"status":"NS"},
        {"date":"06/16","time":"03:00","home":"義大利","away":"克羅埃西亞","home_g":None,"away_g":None,"status":"NS"},
        {"date":"06/16","time":"21:00","home":"日本","away":"韓國","home_g":None,"away_g":None,"status":"NS"},
    ]

# ── 圖片基底 ─────────────────────────────────────────────
def new_canvas():
    img  = Image.new("RGB", (1080, 1350), BG)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0,0,1080,8], fill=GREEN)
    draw.rectangle([0,1342,1080,1350], fill=GREEN)
    return img, draw

def draw_footer(draw, linktree=True):
    W, H = 1080, 1350
    draw.rectangle([60,H-110,W-60,H-109], fill=GRAY)
    if linktree:
        draw.text((W//2,H-75), "🔗 串流/球衣/周邊 → 連結在 bio！", font=font(26), fill=GOLD, anchor="mm")
        draw.text((W//2,H-38), LINKTREE_URL, font=font(20), fill=GRAY, anchor="mm")
    else:
        draw.text((W//2,H-75), "追蹤帳號 不漏球 ⚽", font=font(28), fill=GREEN, anchor="mm")
        draw.text((W//2,H-38), "@your_football_account", font=font(20), fill=GRAY, anchor="mm")

def save_img(img, path="output/schedule.png"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, quality=95)
    print(f"✅ 圖片：{path}")
    return path

# ── 1. 本週賽程圖 ────────────────────────────────────────
def make_weekly(fixtures):
    img, draw = new_canvas()
    W = 1080
    draw.text((W//2,70),  "⚽ 本週足球賽程", font=font(52), fill=WHITE, anchor="mm")
    draw.text((W//2,125), f"台灣時間 · {datetime.now().strftime('%Y.%m.%d')} 更新", font=font(26), fill=GRAY, anchor="mm")
    draw.rectangle([60,155,W-60,158], fill=GRAY)
    card_h, card_gap = 150, 12
    for i, f in enumerate(fixtures[:6]):
        y = 170 + i * (card_h + card_gap)
        draw.rectangle([50,y,W-50,y+card_h], fill=CARD)
        draw.rectangle([50,y,180,y+card_h],  fill=GREEN)
        draw.text((115,y+38),  f["date"],  font=font(22), fill=WHITE,        anchor="mm")
        draw.text((115,y+75),  f["time"],  font=font(28), fill=WHITE,        anchor="mm")
        draw.text((115,y+112), "台灣時間", font=font(17), fill=(200,255,200), anchor="mm")
        score = "VS" if f["status"] == "NS" else f"{f['home_g']} - {f['away_g']}"
        score_color = GOLD if f["status"] == "FT" else WHITE
        draw.text((310,   y+75), f["home"], font=font(30), fill=WHITE,       anchor="mm")
        draw.text((W//2,  y+75), score,     font=font(30), fill=score_color, anchor="mm")
        draw.text((W-310, y+75), f["away"], font=font(30), fill=WHITE,       anchor="mm")
    draw_footer(draw, linktree=True)
    return save_img(img)

# ── 2. 今日賽程圖 ────────────────────────────────────────
def make_daily(fixtures):
    img, draw = new_canvas()
    W = 1080
    today_str = datetime.now().strftime("%m/%d")
    draw.text((W//2,70),  f"⚽ 今日賽程 {today_str}", font=font(52), fill=WHITE, anchor="mm")
    draw.text((W//2,125), "台灣時間，準時開賽！", font=font(26), fill=GRAY, anchor="mm")
    draw.rectangle([60,155,W-60,158], fill=GRAY)
    card_h, card_gap = 160, 15
    for i, f in enumerate(fixtures[:5]):
        y = 175 + i * (card_h + card_gap)
        draw.rectangle([50,y,W-50,y+card_h], fill=CARD)
        draw.rectangle([50,y,180,y+card_h],  fill=GREEN)
        draw.text((115,y+50),  f["time"],  font=font(34), fill=WHITE,        anchor="mm")
        draw.text((115,y+110), "開賽",     font=font(20), fill=(200,255,200), anchor="mm")
        draw.text((310,   y+80), f["home"], font=font(32), fill=WHITE, anchor="mm")
        draw.text((W//2,  y+80), "VS",      font=font(32), fill=GOLD,  anchor="mm")
        draw.text((W-310, y+80), f["away"], font=font(32), fill=WHITE, anchor="mm")
    draw_footer(draw, linktree=True)
    return save_img(img)

# ── 3. 賽後比分圖 ────────────────────────────────────────
def make_result(fixtures):
    img, draw = new_canvas()
    W = 1080
    draw.text((W//2,70),  "🏆 今日賽果", font=font(52), fill=GOLD,  anchor="mm")
    draw.text((W//2,125), f"{datetime.now().strftime('%Y.%m.%d')} 完賽", font=font(26), fill=GRAY, anchor="mm")
    draw.rectangle([60,155,W-60,158], fill=GRAY)
    card_h, card_gap = 160, 15
    for i, f in enumerate(fixtures[:5]):
        y = 175 + i * (card_h + card_gap)
        hg, ag = f.get("home_g", 0) or 0, f.get("away_g", 0) or 0
        winner = "home" if hg > ag else ("away" if ag > hg else "draw")
        draw.rectangle([50,y,W-50,y+card_h], fill=CARD)
        hw = WHITE if winner != "away" else GRAY
        aw = WHITE if winner != "home" else GRAY
        draw.text((250,   y+80), f["home"],    font=font(30), fill=hw,   anchor="mm")
        draw.text((W//2,  y+80), f"{hg} - {ag}", font=font(38), fill=GOLD, anchor="mm")
        draw.text((W-250, y+80), f["away"],    font=font(30), fill=aw,   anchor="mm")
        result_text = "主場勝" if winner=="home" else ("客場勝" if winner=="away" else "平局")
        draw.text((W//2,  y+120), result_text, font=font(20), fill=GRAY, anchor="mm")
    draw_footer(draw, linktree=True)
    return save_img(img)

# ── Caption ──────────────────────────────────────────────
def make_caption(fixtures, post_type):
    cta = f"\n\n🔗 看球串流＆球衣推薦 → {LINKTREE_URL}\n（連結在 bio）"
    tags = "\n\n#世界盃 #足球 #賽程 #WorldCup2026 #football #台灣足球"

    if post_type == "weekly":
        lines = ["⚽ 本週足球賽程（台灣時間）\n"]
        for f in fixtures:
            lines.append(f"📅 {f['date']} {f['time']}　{f['home']} vs {f['away']}")
        return "\n".join(lines) + cta + tags

    elif post_type == "daily":
        lines = [f"⚽ 今日賽程 {datetime.now().strftime('%m/%d')}（台灣時間）\n"]
        for f in fixtures:
            lines.append(f"🕐 {f['time']}　{f['home']} vs {f['away']}")
        lines.append("\n🔔 追蹤帳號，比賽開始前提醒你！")
        return "\n".join(lines) + cta + tags

    elif post_type == "result":
        lines = ["🏆 今日賽果\n"]
        for f in fixtures:
            hg, ag = f.get("home_g",0) or 0, f.get("away_g",0) or 0
            lines.append(f"✅ {f['home']} {hg} - {ag} {f['away']}")
        return "\n".join(lines) + cta + tags

    return "" + cta + tags

# ── 上傳 & 發布 ──────────────────────────────────────────
def upload_image(path):
    with open(path,"rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    res = requests.post("https://api.imgbb.com/1/upload",
                        data={"key":IMGBB_API_KEY,"image":b64}, timeout=30)
    url = res.json()["data"]["url"]
    print(f"✅ 上傳：{url}")
    return url

def post_to_instagram(image_url, caption):
    res = requests.post(f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={"image_url":image_url,"caption":caption,"access_token":IG_ACCESS_TOKEN}, timeout=15)
    print(f"建立媒體：{res.json()}")
    cid = res.json().get("id")
    if not cid:
        print("❌ 失敗"); return
    print("⏳ 等待 30 秒...")
    time.sleep(30)
    res = requests.post(f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
        data={"creation_id":cid,"access_token":IG_ACCESS_TOKEN}, timeout=15)
    print(f"發布：{res.json()}")
    print("✅ 成功！" if res.json().get("id") else "❌ 失敗")

# ── 主程式 ──────────────────────────────────────────────
def main():
    print(f"🤖 Football Bot 啟動 | 模式：{POST_TYPE}")
    print(f"字體存在：{os.path.exists(FONT_PATH)}")

    if POST_TYPE == "weekly":
        fixtures = get_fixtures(0, 7) if API_FOOTBALL_KEY else []
        fixtures = fixtures or mock_fixtures()
        print(f"比賽數量：{len(fixtures)}")
        img_path = make_weekly(fixtures)
        caption  = make_caption(fixtures, "weekly")

    elif POST_TYPE == "daily":
        fixtures = get_fixtures(0, 1) if API_FOOTBALL_KEY else []
        fixtures = fixtures or mock_fixtures()[:3]
        if not fixtures:
            print("今日無比賽，跳過發文"); return
        img_path = make_daily(fixtures)
        caption  = make_caption(fixtures, "daily")

    elif POST_TYPE == "result":
        fixtures = get_fixtures(-1, 0) if API_FOOTBALL_KEY else []
        fixtures = [f for f in fixtures if f["status"] == "FT"]
        fixtures = fixtures or mock_fixtures()[:3]
        if not fixtures:
            print("無完賽資料，跳過"); return
        img_path = make_result(fixtures)
        caption  = make_caption(fixtures, "result")

    else:
        print(f"未知模式：{POST_TYPE}"); return

    if IG_ACCESS_TOKEN and IMGBB_API_KEY:
        post_to_instagram(upload_image(img_path), caption)
    else:
        print("⚠️ 未設定 Token，跳過發布")
    print("✅ 完成！")

if __name__ == "__main__":
    main()
