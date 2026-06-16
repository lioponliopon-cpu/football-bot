"""
Football Schedule Bot
自動抓取賽程 → 生成圖片 → 發布到 Instagram
"""

import os
import json
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import textwrap

# ── 設定區（填入你的 API Keys）──────────────────────────
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")
IG_ACCESS_TOKEN  = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID       = os.environ.get("IG_USER_ID", "")
IMGBB_API_KEY    = os.environ.get("IMGBB_API_KEY", "")   # 免費圖床，上傳圖片用

# ── 顏色主題 ────────────────────────────────────────────
COLORS = {
    "bg":        "#0D1117",   # 深夜黑背景
    "card":      "#161B22",   # 卡片背景
    "accent":    "#238636",   # 足球綠
    "accent2":   "#1F6FEB",   # 藍色點綴
    "text":      "#F0F6FC",   # 主文字白
    "subtext":   "#8B949E",   # 次要文字灰
    "border":    "#30363D",   # 邊框
    "gold":      "#F0B429",   # 金色（重要場次）
}

def hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# ── 1. 抓取賽程 ─────────────────────────────────────────
def fetch_fixtures(league_id=1, season=2026, days_ahead=7):
    """
    從 API-Football 抓取未來賽程
    league_id: 1 = 世界盃, 2 = 歐冠, 39 = 英超
    免費方案每天 100 次請求，夠用
    """
    today = datetime.now()
    end   = today + timedelta(days=days_ahead)

    url = "https://v3.football.api-sports.io/fixtures"
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    params  = {
        "league": league_id,
        "season": season,
        "from":   today.strftime("%Y-%m-%d"),
        "to":     end.strftime("%Y-%m-%d"),
        "timezone": "Asia/Taipei",
    }

    res = requests.get(url, headers=headers, params=params, timeout=10)
    data = res.json()

    fixtures = []
    for f in data.get("response", []):
        fixture  = f["fixture"]
        teams    = f["teams"]
        goals    = f["goals"]
        status   = fixture["status"]["short"]

        # 台灣時間
        utc_time = datetime.fromisoformat(fixture["date"].replace("Z", "+00:00"))
        tw_time  = utc_time + timedelta(hours=8)

        fixtures.append({
            "date":      tw_time.strftime("%m/%d"),
            "time":      tw_time.strftime("%H:%M"),
            "home":      teams["home"]["name"],
            "away":      teams["away"]["name"],
            "home_logo": teams["home"]["logo"],
            "away_logo": teams["away"]["logo"],
            "score":     f"{goals['home']} - {goals['away']}" if status == "FT" else "VS",
            "status":    status,
        })

    return fixtures[:8]  # 最多顯示8場

# ── 2. 示範用假資料（還沒有 API Key 時測試用）────────────
def mock_fixtures():
    return [
        {"date":"06/14","time":"21:00","home":"巴西","away":"阿根廷","score":"VS","status":"NS"},
        {"date":"06/14","time":"00:00","home":"法國","away":"西班牙","score":"VS","status":"NS"},
        {"date":"06/15","time":"18:00","home":"德國","away":"英格蘭","score":"VS","status":"NS"},
        {"date":"06/15","time":"21:00","home":"葡萄牙","away":"荷蘭","score":"VS","status":"NS"},
        {"date":"06/16","time":"03:00","home":"義大利","away":"克羅埃西亞","score":"VS","status":"NS"},
        {"date":"06/16","time":"21:00","home":"日本","away":"韓國","score":"VS","status":"NS"},
    ]

# ── 3. 生成圖片 ─────────────────────────────────────────
def generate_schedule_image(fixtures, output_path="output/schedule.png"):
    W, H = 1080, 1350  # IG 直式最佳尺寸

    img  = Image.new("RGB", (W, H), hex_to_rgb(COLORS["bg"]))
    draw = ImageDraw.Draw(img)

    # ── 載入中文字體（從 repo 內的 assets 資料夾）
    def load_font(size):
        font_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "NotoSansCJK.otf")
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception as e:
                print(f"字體載入失敗：{e}")
        return ImageFont.load_default()

    font_title  = load_font(52)
    font_sub    = load_font(28)
    font_match  = load_font(34)
    font_time   = load_font(26)
    font_small  = load_font(22)

    # ── Header ──
    # 綠色頂部橫條
    draw.rectangle([0, 0, W, 8], fill=hex_to_rgb(COLORS["accent"]))

    # 標題
    title = "⚽ 本週足球賽程"
    draw.text((W//2, 70), title, font=font_title,
              fill=hex_to_rgb(COLORS["text"]), anchor="mm")

    # 副標題
    today = datetime.now().strftime("%Y.%m.%d")
    sub   = f"台灣時間 · {today} 更新"
    draw.text((W//2, 125), sub, font=font_small,
              fill=hex_to_rgb(COLORS["subtext"]), anchor="mm")

    # 分隔線
    draw.rectangle([60, 155, W-60, 158], fill=hex_to_rgb(COLORS["border"]))

    # ── 比賽卡片 ──
    card_h   = 155
    card_gap = 18
    start_y  = 180

    for i, f in enumerate(fixtures[:6]):
        y = start_y + i * (card_h + card_gap)

        # 卡片背景
        draw.rounded_rectangle(
            [50, y, W-50, y+card_h],
            radius=16,
            fill=hex_to_rgb(COLORS["card"]),
            outline=hex_to_rgb(COLORS["border"]),
            width=1,
        )

        # 左側時間欄
        draw.rounded_rectangle(
            [50, y, 180, y+card_h],
            radius=16,
            fill=hex_to_rgb(COLORS["accent"]),
        )
        draw.rectangle([150, y, 180, y+card_h], fill=hex_to_rgb(COLORS["accent"]))

        draw.text((115, y+40),  f["date"], font=font_small,
                  fill=(255,255,255), anchor="mm")
        draw.text((115, y+80),  f["time"], font=font_time,
                  fill=(255,255,255), anchor="mm")
        draw.text((115, y+112), "台灣時間",  font=load_font(17),
                  fill=(200,255,200), anchor="mm")

        # 主隊名稱
        draw.text((310, y+card_h//2), f["home"], font=font_match,
                  fill=hex_to_rgb(COLORS["text"]), anchor="mm")

        # VS / 比分
        score_color = COLORS["gold"] if f["status"] == "FT" else COLORS["subtext"]
        draw.text((W//2, y+card_h//2), f["score"], font=font_match,
                  fill=hex_to_rgb(score_color), anchor="mm")

        # 客隊名稱
        draw.text((W-310, y+card_h//2), f["away"], font=font_match,
                  fill=hex_to_rgb(COLORS["text"]), anchor="mm")

    # ── Footer ──
    footer_y = H - 100
    draw.rectangle([0, footer_y-1, W, footer_y+1], fill=hex_to_rgb(COLORS["border"]))

    draw.text((W//2, footer_y+35), "追蹤帳號 不漏球 ⚽",
              font=font_sub, fill=hex_to_rgb(COLORS["accent"]), anchor="mm")
    draw.text((W//2, footer_y+72), "@your_football_account",
              font=font_small, fill=hex_to_rgb(COLORS["subtext"]), anchor="mm")

    # 底部綠條
    draw.rectangle([0, H-8, W, H], fill=hex_to_rgb(COLORS["accent"]))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, quality=95)
    print(f"✅ 圖片已生成：{output_path}")
    return output_path

# ── 4. 上傳圖片到免費圖床 imgbb ─────────────────────────
def upload_image(image_path):
    """IG API 需要公開 URL，用 imgbb 免費圖床"""
    with open(image_path, "rb") as f:
        import base64
        img_b64 = base64.b64encode(f.read()).decode()

    res = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": img_b64},
        timeout=30,
    )
    url = res.json()["data"]["url"]
    print(f"✅ 圖片已上傳：{url}")
    return url

# ── 5. 發布到 Instagram ──────────────────────────────────
def post_to_instagram(image_url, caption):
    """透過 Meta Graph API 發布貼文"""

    # Step 1: 建立媒體容器
    create_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media"
    res = requests.post(create_url, data={
        "image_url":    image_url,
        "caption":      caption,
        "access_token": IG_ACCESS_TOKEN,
    }, timeout=15)
    container_id = res.json().get("id")

    if not container_id:
        print(f"❌ 建立媒體失敗：{res.json()}")
        return

    # Step 2: 發布
    publish_url = f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish"
    res = requests.post(publish_url, data={
        "creation_id":  container_id,
        "access_token": IG_ACCESS_TOKEN,
    }, timeout=15)

    if res.json().get("id"):
        print(f"✅ 已發布到 Instagram！貼文ID：{res.json()['id']}")
    else:
        print(f"❌ 發布失敗：{res.json()}")

# ── 6. 生成 Caption ─────────────────────────────────────
def generate_caption(fixtures):
    lines = ["⚽ 本週足球賽程（台灣時間）\n"]
    for f in fixtures[:6]:
        lines.append(f"📅 {f['date']} {f['time']}")
        lines.append(f"   {f['home']} vs {f['away']}\n")
    lines += [
        "━━━━━━━━━━━━━━━",
        "🔔 追蹤帳號，開賽前自動通知！",
        "",
        "#世界盃 #足球 #賽程 #WorldCup2026",
        "#足球賽程 #足球台灣 #football",
    ]
    return "\n".join(lines)

# ── 主程式 ──────────────────────────────────────────────
def main():
    print("🤖 Football Bot 啟動中...")

    # 自動查詢正確的 IG USER ID
    if IG_ACCESS_TOKEN:
        res = requests.get(
            "https://graph.facebook.com/v19.0/me/accounts",
            params={"access_token": IG_ACCESS_TOKEN, "fields": "id,name,instagram_business_account"},
        )
        print(f"📋 帳號資料：{res.json()}")

    # 抓賽程（有 API Key 用真實資料，否則用假資料）
    if API_FOOTBALL_KEY:
        print("📡 從 API 抓取真實賽程...")
        fixtures = fetch_fixtures(league_id=1, season=2026)
    else:
        print("⚠️  使用示範資料（請設定 API_FOOTBALL_KEY）")
        fixtures = mock_fixtures()

    # 生成圖片
    img_path = generate_schedule_image(fixtures, "output/schedule.png")

    # 發布到 IG（有設定 Token 才發）
    if IG_ACCESS_TOKEN and IMGBB_API_KEY:
        image_url = upload_image(img_path)
        caption   = generate_caption(fixtures)
        post_to_instagram(image_url, caption)
    else:
        print("⚠️  未設定 IG Token，跳過發布（圖片已存在 output/ 資料夾）")

    print("✅ 完成！")

if __name__ == "__main__":
    main()
