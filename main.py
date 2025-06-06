import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import os
import json

# 📌 환경 변수에서 API Key 및 서비스 계정 JSON 불러오기
serp_api_key = os.environ['SERPAPI_KEY']
google_json_raw = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']

# 🔐 credentials.json 파일 생성
with open("credentials.json", "w") as f:
    json.dump(json.loads(google_json_raw), f)

# 📅 오늘 날짜
today = datetime.today().strftime("%Y-%m-%d")

# 📌 Google Sheets 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# 📄 시트 열기
spreadsheet = gc.open("BrandPulse_Lotte_Hotel")
worksheet = spreadsheet.worksheet("InstagramData")
insight_sheet = spreadsheet.worksheet("InstagramInsights")

# 📋 브랜드 목록
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]

# 📈 인스타그램 데이터 수집
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

    return posts, [today, brand, post_count, avg_likes, avg_comments, hashtags, sentiment]

# 🧠 키워드 및 요약 추출 함수 (임시 룰 기반, GPT 적용 예정)
def extract_keywords_and_summary(posts, brand):
    all_titles = " ".join([p.get("title", "") for p in posts])
    words = [word.strip("#., ") for word in all_titles.split()]
    keywords = list(set([w for w in words if len(w) > 4 and brand not in w and "instagram" not in w.lower()]))
    summary = all_titles[:80] + "..." if all_titles else "요약 없음"
    return ", ".join(keywords[:5]), summary

# ✅ 기존 InstagramData 시트 확인 (중복 방지)
existing_dates = worksheet.col_values(1)
existing_brands = worksheet.col_values(2)
existing_today_rows = set((d, b) for d, b in zip(existing_dates, existing_brands) if d == today)

# ✅ 기존 InstagramInsights 시트 확인
insight_rows = insight_sheet.get_all_values()
insight_existing = set((row[0], row[1]) for row in insight_rows[1:])  # 헤더 제외

# 📤 두 시트 모두 업데이트
for brand in brands:
    # InstagramData
    if (today, brand) not in existing_today_rows:
        posts, row = fetch_instagram_data(brand)
        worksheet.append_row(row)
        print(f"[InstagramData] {brand} 데이터 추가 완료")
    else:
        print(f"[InstagramData] {brand} 이미 존재 - 스킵")

    # InstagramInsights
    if (today, brand) not in insight_existing:
        posts, _ = fetch_instagram_data(brand)
        keywords, summary = extract_keywords_and_summary(posts, brand)
        insight_sheet.append_row([today, brand, keywords, summary])
        print(f"[InstagramInsights] {brand} 인사이트 추가 완료")
    else:
        print(f"[InstagramInsights] {brand} 인사이트 이미 존재 - 스킵")
