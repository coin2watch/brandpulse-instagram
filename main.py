import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime

# 구글 시트 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# 시트 열기
spreadsheet = gc.open("BrandPulse")
worksheet = spreadsheet.worksheet("InstagramData")

# 브랜드 리스트
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]
today = datetime.today().strftime("%Y-%m-%d")

def fetch_instagram_data(brand):
    url = f"https://serpapi.com/search.json?engine=google&q=site:instagram.com {brand}&api_key=YOUR_SERPAPI_KEY"
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