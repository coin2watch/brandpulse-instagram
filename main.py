import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import os
import re

# 인증 및 환경 설정
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# 구글 시트 접근
spreadsheet = gc.open("BrandPulse_Lotte_Hotel")
worksheet = spreadsheet.worksheet("InstagramInsights")

# 브랜드 리스트
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]
today = datetime.today().strftime("%Y-%m-%d")

# SerpApi 키
serp_api_key = os.environ['SERPAPI_KEY']

# 각 브랜드의 인스타그램 포스트 제목 수집 및 요약
def fetch_instagram_insights(brand):
    query = f"site:instagram.com {brand}"
    url = f"https://serpapi.com/search.json?engine=google&q={query}&api_key={serp_api_key}"
    response = requests.get(url)
    data = response.json()

    posts = data.get("organic_results", [])[:10]
    titles = [p.get("title", "") for p in posts if "title" in p]

    full_text = " ".join(titles)
    keywords = extract_keywords(full_text)
    summary = summarize_text(full_text)

    return [today, brand, ", ".join(keywords), summary]

# 키워드 추출 함수 (단순 빈도 기반)
def extract_keywords(text):
    words = re.findall(r"\b[\w가-힣]{2,}\b", text.lower())
    stopwords = ["instagram", "com"] + [brand.lower() for brand in brands]
    filtered = [w for w in words if w not in stopwords]
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_keywords[:5]]

# 텍스트 요약 (간단한 룰 기반)
def summarize_text(text):
    sentences = re.split(r'[.!?]', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return sentences[0] if sentences else "No summary."

# 중복 방지 체크
existing_rows = worksheet.get_all_values()
existing_keys = {(row[0], row[1]) for row in existing_rows[1:]}

# 데이터 수집 및 시트 추가
for brand in brands:
    if (today, brand) in existing_keys:
        print(f"{brand} 데이터 이미 존재 - 스킵")
        continue

    row = fetch_instagram_insights(brand)
    worksheet.append_row(row)
    print(f"{brand} 인사이트 저장 완료")
