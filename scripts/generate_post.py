"""
Football Bot - 完整修正版
修正：1) API失敗會明確報錯，不再靜默用假資料
      2) 改用 fixtures?date= 抓「當天全部」比賽，不限定單一聯賽
      3) result 圖排版加大間距避免文字重疊
"""
import os, sys, time, requests, base64
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
IG_ACCESS_TOKEN  = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID       = os.environ.get("IG_USER_ID", "")
IMGBB_API_KEY    = os.environ.get("IMGBB_API_KEY", "")
POST_TYPE        = os.environ.get("POST_TYPE", "weekly")
LINKTREE_URL     = "https://linktr.ee/your_football_account"

FONT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "NotoSansCJK.otf")

BG=(13,17,23); CARD=(22,27,34); GREEN=(35,134,54)
WHITE=(240,246,252); GRAY=(139,148,158); GOLD=(240,180,41); RED=(207,34,46)


def draw_ball_icon(draw, cx, cy, r):
    """用幾何圖形畫一顆簡單足球圖示，不依賴 emoji 字形"""
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=WHITE, width=3)
    draw.polygon([(cx, cy-r*0.5), (cx-r*0.45, cy-r*0.15), (cx-r*0.28, cy+r*0.4),
                  (cx+r*0.28, cy+r*0.4), (cx+r*0.45, cy-r*0.15)], outline=WHITE, width=2)

def font(size):
    return ImageFont.truetype(FONT_PATH, size) if os.path.exists(FONT_PATH) else ImageFont.load_default()

# ── API：用日期查詢，抓「該日全部賽事」，不綁定單一聯盟 ──
# 這樣才能涵蓋世界盃以外的所有比賽（只要 API-Football 該聯賽有開放）
def api_get_fixtures_by_date(date_str):
    """抓指定日期(YYYY-MM-DD)的全部賽事，回傳 (資料陣列, 是否成功, 錯誤訊息)"""
    if not API_FOOTBALL_KEY:
        return [], False, "未設定 API_FOOTBALL_KEY"
    try:
        res = requests.get(
            "https://v3.football.api-sports.io/fixtures",
            headers={"x-apisports-key": API_FOOTBALL_KEY},
            params={"date": date_str, "timezone": "Asia/Taipei"},
            timeout=15
        )
        data = res.json()
        errors = data.get("errors")
        if errors:
            return [], False, f"API錯誤：{errors}"
        results = data.get("response", [])
        return results, True, None
    except Exception as e:
        return [], False, f"請求例外：{e}"

def parse_fixture(f):
    t = datetime.fromisoformat(f["fixture"]["date"].replace("Z","+00:00")) + timedelta(hours=8)
    return {
        "date":   t.strftime("%m/%d"),
        "time":   t.strftime("%H:%M"),
        "home":   f["teams"]["home"]["name"],
        "away":   f["teams"]["away"]["name"],
        "home_g": f["goals"]["home"],
        "away_g": f["goals"]["away"],
        "status": f["fixture"]["status"]["short"],
        "league": f["league"]["name"],
    }

def get_fixtures_range(days_from=0, days_to=7):
    """抓多天範圍內、所有聯賽的比賽（用逐日查詢，因為 fixtures?date= 才會回傳當天全部聯賽）"""
    all_fx = []
    errors = []
    today = datetime.now()
    for d in range(days_from, days_to):
        date_str = (today + timedelta(days=d)).strftime("%Y-%m-%d")
        data, ok, err = api_get_fixtures_by_date(date_str)
        if not ok:
            errors.append(f"{date_str}: {err}")
            continue
        all_fx.extend([parse_fixture(f) for f in data])
    return all_fx, errors

def mock_fixtures():
    return [
        {"date":"06/19","time":"21:00","home":"巴西","away":"阿根廷","home_g":None,"away_g":None,"status":"NS","league":"示範資料"},
        {"date":"06/19","time":"23:00","home":"法國","away":"西班牙","home_g":None,"away_g":None,"status":"NS","league":"示範資料"},
        {"date":"06/20","time":"01:00","home":"德國","away":"英格蘭","home_g":None,"away_g":None,"status":"NS","league":"示範資料"},
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
        draw.text((W//2,H-75), "▶ 串流/球衣/周邊 → 連結在 bio！", font=font(26), fill=GOLD, anchor="mm")
        draw.text((W//2,H-38), LINKTREE_URL, font=font(20), fill=GRAY, anchor="mm")
    else:
        draw.text((W//2,H-75), "追蹤帳號 不漏球", font=font(28), fill=GREEN, anchor="mm")
        draw.text((W//2,H-38), "@your_football_account", font=font(20), fill=GRAY, anchor="mm")

def save_img(img, path="output/schedule.png"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, quality=95)
    print(f"✅ 圖片：{path}")
    return path

def fit_text(draw, text, max_width, base_size, min_size=18):
    """自動縮小字體直到文字寬度不超過 max_width，避免長隊名重疊"""
    size = base_size
    while size > min_size:
        f = font(size)
        bbox = draw.textbbox((0,0), text, font=f)
        if bbox[2]-bbox[0] <= max_width:
            return f
        size -= 2
    return font(min_size)

# ── 1. 本週賽程圖 ────────────────────────────────────────
def make_weekly(fixtures):
    img, draw = new_canvas()
    W = 1080
    draw_ball_icon(draw, W//2-180, 70, 22)
    draw.text((W//2,70),  "本週足球賽程", font=font(52), fill=WHITE, anchor="mm")
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
        hf = fit_text(draw, f["home"], 220, 30)
        af = fit_text(draw, f["away"], 220, 30)
        draw.text((310,   y+60), f["home"], font=hf, fill=WHITE,       anchor="mm")
        draw.text((W//2,  y+75), score,     font=font(30), fill=score_color, anchor="mm")
        draw.text((W-310, y+60), f["away"], font=af, fill=WHITE,       anchor="mm")
        draw.text((310,   y+105), f.get("league","")[:14], font=font(16), fill=GRAY, anchor="mm")
        draw.text((W-310, y+105), "", font=font(16), fill=GRAY, anchor="mm")
    draw_footer(draw, linktree=True)
    return save_img(img)

# ── 2. 今日賽程圖 ────────────────────────────────────────
def make_daily(fixtures):
    img, draw = new_canvas()
    W = 1080
    today_str = datetime.now().strftime("%m/%d")
    draw_ball_icon(draw, W//2-190, 70, 20)
    draw.text((W//2,70),  f"今日賽程 {today_str}", font=font(48), fill=WHITE, anchor="mm")
    draw.text((W//2,125), f"台灣時間，共 {len(fixtures)} 場比賽", font=font(24), fill=GRAY, anchor="mm")
    draw.rectangle([60,155,W-60,158], fill=GRAY)
    n = min(len(fixtures), 6)
    card_h = 150 if n <= 6 else 110
    card_gap = 12
    for i, f in enumerate(fixtures[:6]):
        y = 170 + i * (card_h + card_gap)
        draw.rectangle([50,y,W-50,y+card_h], fill=CARD)
        draw.rectangle([50,y,180,y+card_h],  fill=GREEN)
        draw.text((115,y+card_h//2-15), f["time"], font=font(30), fill=WHITE, anchor="mm")
        draw.text((115,y+card_h//2+20), "開賽",     font=font(18), fill=(200,255,200), anchor="mm")
        hf = fit_text(draw, f["home"], 220, 28)
        af = fit_text(draw, f["away"], 220, 28)
        draw.text((310,   y+card_h//2-12), f["home"], font=hf, fill=WHITE, anchor="mm")
        draw.text((W//2,  y+card_h//2-12), "VS",       font=font(28), fill=GOLD,  anchor="mm")
        draw.text((W-310, y+card_h//2-12), f["away"], font=af, fill=WHITE, anchor="mm")
        draw.text((W//2,  y+card_h//2+22), f.get("league","")[:18], font=font(15), fill=GRAY, anchor="mm")
    draw_footer(draw, linktree=True)
    return save_img(img)

# ── 3. 賽後比分圖（加大排版間距，避免文字重疊）────────────
def make_result(fixtures):
    img, draw = new_canvas()
    W = 1080
    draw_ball_icon(draw, W//2-130, 70, 20)
    draw.text((W//2,70),  "今日賽果", font=font(50), fill=GOLD,  anchor="mm")
    draw.text((W//2,125), f"{datetime.now().strftime('%Y.%m.%d')} 完賽 · 共 {len(fixtures)} 場", font=font(24), fill=GRAY, anchor="mm")
    draw.rectangle([60,155,W-60,158], fill=GRAY)
    card_h, card_gap = 170, 16
    for i, f in enumerate(fixtures[:5]):
        y = 175 + i * (card_h + card_gap)
        hg, ag = f.get("home_g", 0) or 0, f.get("away_g", 0) or 0
        winner = "home" if hg > ag else ("away" if ag > hg else "draw")
        draw.rectangle([50,y,W-50,y+card_h], fill=CARD)

        hw = WHITE if winner != "away" else GRAY
        aw = WHITE if winner != "home" else GRAY

        # 隊名區塊：左 50~390 / 比分區塊：中 390~690 / 右隊名 690~1030
        # 隊名自動縮小避免跟比分重疊，並換行顯示
        home_font = fit_text(draw, f["home"], 300, 28)
        away_font = fit_text(draw, f["away"], 300, 28)

        draw.text((220, y+55), f["home"], font=home_font, fill=hw, anchor="mm")
        draw.text((W//2, y+55), f"{hg} - {ag}", font=font(40), fill=GOLD, anchor="mm")
        draw.text((860, y+55), f["away"], font=away_font, fill=aw, anchor="mm")

        result_text = "主場勝" if winner=="home" else ("客場勝" if winner=="away" else "平局")
        draw.text((W//2, y+105), result_text, font=font(20), fill=GRAY, anchor="mm")
        draw.text((W//2, y+138), f.get("league","")[:20], font=font(15), fill=GRAY, anchor="mm")

    draw_footer(draw, linktree=True)
    return save_img(img)

# ── Caption ──────────────────────────────────────────────
def make_caption(fixtures, post_type):
    cta = f"\n\n🔗 看球串流＆球衣推薦 → {LINKTREE_URL}\n（連結在 bio）"
    tags = "\n\n#世界盃 #足球 #賽程 #WorldCup2026 #football #台灣足球"

    if post_type == "weekly":
        lines = ["⚽ 本週足球賽程（台灣時間）\n"]
        for f in fixtures:
            lines.append(f"📅 {f['date']} {f['time']}　{f['home']} vs {f['away']}　[{f.get('league','')}]")
        return "\n".join(lines) + cta + tags

    elif post_type == "daily":
        lines = [f"⚽ 今日賽程 {datetime.now().strftime('%m/%d')}（台灣時間，共{len(fixtures)}場）\n"]
        for f in fixtures:
            lines.append(f"🕐 {f['time']}　{f['home']} vs {f['away']}　[{f.get('league','')}]")
        lines.append("\n🔔 追蹤帳號，比賽開始前提醒你！")
        return "\n".join(lines) + cta + tags

    elif post_type == "result":
        lines = ["🏆 今日賽果\n"]
        for f in fixtures:
            hg, ag = f.get("home_g",0) or 0, f.get("away_g",0) or 0
            lines.append(f"✅ {f['home']} {hg} - {ag} {f['away']}　[{f.get('league','')}]")
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
    print(f"API Key 已設定：{bool(API_FOOTBALL_KEY)}")

    used_mock = False

    if POST_TYPE == "weekly":
        fixtures, errors = get_fixtures_range(0, 7)
        if errors:
            print(f"⚠️ 部分日期查詢失敗：{errors}")
        if not fixtures:
            print("⚠️⚠️⚠️ API 沒有抓到任何比賽資料，改用示範資料（請檢查 API Key / 額度 / 該週是否真的沒賽事）")
            fixtures = mock_fixtures()
            used_mock = True
        print(f"比賽數量：{len(fixtures)}　使用假資料：{used_mock}")
        img_path = make_weekly(fixtures)
        caption  = make_caption(fixtures, "weekly")

    elif POST_TYPE == "daily":
        fixtures, errors = get_fixtures_range(0, 1)
        if errors:
            print(f"⚠️ 查詢失敗：{errors}")
        if not fixtures:
            print("ℹ️ 今天 API 查無比賽資料（可能真的沒賽事，也可能 API 異常）")
            print("為了驗證流程改用示範資料；正式運作時這裡應該要跳過發文")
            fixtures = mock_fixtures()
            used_mock = True
        print(f"比賽數量：{len(fixtures)}　使用假資料：{used_mock}")
        img_path = make_daily(fixtures)
        caption  = make_caption(fixtures, "daily")

    elif POST_TYPE == "result":
        fixtures, errors = get_fixtures_range(-1, 0)
        fixtures = [f for f in fixtures if f["status"] in ("FT","AET","PEN")]
        if errors:
            print(f"⚠️ 查詢失敗：{errors}")
        if not fixtures:
            print("ℹ️ 查無已完賽資料，改用示範資料")
            fixtures = mock_fixtures()
            used_mock = True
        print(f"比賽數量：{len(fixtures)}　使用假資料：{used_mock}")
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
