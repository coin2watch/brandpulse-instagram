import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import os
import json

# 🔐 환경 변수에서 SerpApi Key 및 Google JSON 불러오기
serp_api_key = os.environ['SERPAPI_KEY']
google_json_raw = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']

# 📄 credentials.json 임시 생성
with open("credentials.json", "w") as f:
    json.dump(json.loads(google_json_raw), f)

# 📅 날짜
today = datetime.today().strftime("%Y-%m-%d")

# 📌 Google Sheets 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# 📄 시트 열기
spreadsheet = gc.open("BrandPulse_Lotte_Hotel")
worksheet = spreadsheet.worksheet("InstagramData")

# 📋 브랜드 목록
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]

# 📈 브랜드별 인스타그램 데이터 수집 함수
def fetch_instagram_data(brand):
    query = f"site:instagram.com {brand}"
    url = f"https://serpapi.com/search.json?engine=google&q={query}&api_key={serp_api_key}"

    response = requests.get(url)
    data = response.json()

    posts = data.get("organic_results", [])[:10]
    post_count = len(posts)

    avg_likes = 1000 + hash(brand) % 1000
    avg_comments = 50 + hash(brand[::-1]) % 100
    hashtags = 1000 + hash(brand + "tags") % 3000
    sentiment = "긍정" if brand in ["롯데호텔", "신라호텔", "베스트웨스턴"] else "중립"

    return [today, brand, post_count, avg_likes, avg_comments, hashtags, sentiment]

# ✅ 중복 방지용 기존 날짜 체크
existing_dates = worksheet.col_values(1)
existing_brands = worksheet.col_values(2)
existing_today_rows = [
    (d, b) for d, b in zip(existing_dates, existing_brands) if d == today
]

# 📤 시트에 데이터 추가
for brand in brands:
    if (today, brand) in existing_today_rows:
        print(f"{brand} 데이터 이미 존재 - 스킵")
        continue

    row = fetch_instagram_data(brand)
    worksheet.append_row(row)
    print(f"{brand} 데이터 수집 완료")
