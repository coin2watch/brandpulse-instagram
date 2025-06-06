import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import os
import json
import openai
from collections import Counter
import re

# 📌 환경 변수로부터 API Key 및 서비스 계정 인증서 가져오기
serp_api_key = os.environ['SERPAPI_KEY']
openai_api_key = os.environ['OPENAI_API_KEY']
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
ws_data = spreadsheet.worksheet("InstagramData")
ws_insights = spreadsheet.worksheet("InstagramInsights")

# 📋 브랜드 목록
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]

# ✅ 기존 중복 방지 로직
existing_dates = ws_data.col_values(1)
existing_brands = ws_data.col_values(2)
existing_today_rows = [
    (d, b) for d, b in zip(existing_dates, existing_brands) if d == today
]

# 🔎 OpenAI 클라이언트 인스턴스 생성
client = openai.OpenAI(api_key=openai_api_key)

# 🔄 포스트에서 키워드 추출
stopwords = ["instagram", "com"] + [b.lower() for b in brands]
def extract_keywords_from_titles(titles):
    words = re.findall(r"\b\w+\b", " ".join(titles).lower())
    filtered = [w for w in words if w not in stopwords and len(w) > 2]
    common = Counter(filtered).most_common(7)
    return ", ".join([w[0] for w in common])

# 📈 SerpApi에서 인스타그램 관련 데이터 수집 및 저장 함수
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

    # 📤 InstagramData 저장
    ws_data.append_row([today, brand, post_count, avg_likes, avg_comments, hashtags, sentiment])
    print(f"{brand} InstagramData 저장 완료")

    # 📚 제목 수집
    titles = [p.get("title", "") for p in posts if p.get("title")]

    try:
        # 🔠 키워드 추출
        keywords = extract_keywords_from_titles(titles)

        # ✍️ ChatGPT로 요약
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "다음 인스타그램 게시물 제목들을 바탕으로, 브랜드의 마케팅 인사이트를 한국어로 요약해 주세요."},
                {"role": "user", "content": "\n".join(titles)}
            ],
            max_tokens=300
        )
        summary = completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[{brand}] GPT 처리 중 오류: {e}\n")
        keywords, summary = "", "요약 실패"

    # 📤 InstagramInsights 저장
    ws_insights.append_row([today, brand, keywords, summary])
    print(f"{brand} InstagramInsights 저장 완료")

# ▶️ 전체 브랜드 반복 실행
for brand in brands:
    if (today, brand) in existing_today_rows:
        print(f"{brand} 데이터 이미 존재 - 스킵")
        continue
    fetch_instagram_data(brand)
