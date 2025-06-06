import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import os
import json

# 구글 시트 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# 시트 열기
spreadsheet = gc.open("BrandPulse_Lotte_Hotel")
worksheet = spreadsheet.worksheet("InstagramData")

# 브랜드 리스트
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]
today = datetime.today().strftime("%Y-%m-%d")

# SerpApi Key는 환경변수 또는 secrets에서 불러오기 (예: GitHub Actions 사용 시)
SERP_API_KEY = os.getenv("SERP_API_KEY") or "YOUR_SERPAPI_KEY"


def fetch_instagram_data(brand):
    url = f"https://serpapi.com/search.json?engine=google&q=site:instagram.com {brand}&api_key={SERP_API_KEY}"
    response = requests.get(url)
    data = response.json()

    # 포스트 수 기준 대략 수집
    post_count = len(data.get("organic_results", []))
    avg_likes = 1000 + hash(brand) % 1000  # 예시 수치
    avg_comments = 100 + hash(brand[::-1]) % 100  # 예시 수치
    hashtags = 1500 + hash(brand + 'hashtags') % 1000
    sentiment = "긍정" if "롯데" in brand or "신라" in brand else "중립"

    return [today, brand, post_count, avg_likes, avg_comments, hashtags, sentiment]


for brand in brands:
    row = fetch_instagram_data(brand)
    worksheet.append_row(row)
    print(f"{brand} 데이터 추가 완료: {row}")
