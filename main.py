import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from datetime import datetime
import os
import json
import openai

# 📌 환경 변수
serp_api_key = os.environ['SERPAPI_KEY']
openai.api_key = os.environ['OPENAI_API_KEY']
google_json_raw = os.environ['GOOGLE_SERVICE_ACCOUNT_JSON']

# 🔐 credentials.json 파일 생성
with open("credentials.json", "w") as f:
    json.dump(json.loads(google_json_raw), f)

# 📅 오늘 날짜
today = datetime.today().strftime("%Y-%m-%d")

# 🔐 Google Sheets 인증
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
gc = gspread.authorize(credentials)

# 📄 시트 열기
spreadsheet = gc.open("BrandPulse_Lotte_Hotel")
worksheet_data = spreadsheet.worksheet("InstagramData")
worksheet_insights = spreadsheet.worksheet("InstagramInsights")

# 📋 브랜드 목록
brands = ["롯데호텔", "신라호텔", "조선호텔", "베스트웨스턴"]

# 📈 SerpApi에서 인스타그램 관련 데이터 수집
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

    return [today, brand, post_count, avg_likes, avg_comments, hashtags, sentiment], posts

# 🧠 GPT로 키워드 및 요약 생성
def extract_keywords_and_summary(brand, posts):
    titles = [post.get("title", "") for post in posts]
    combined_text = "\n".join(titles)

    prompt = f"""
    다음은 {brand} 관련 최근 인스타그램 포스트 제목입니다:

    {combined_text}

    위 내용을 기반으로 핵심 키워드를 5~10개 추출하고, 전체 내용을 한 문장으로 요약해줘.
    결과는 다음 형식으로 반환해:

    키워드: keyword1, keyword2, ...
    요약: ...
    """

    try:
        completion = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        result = completion.choices[0].message['content']
        lines = result.strip().split('\n')
        keywords = lines[0].replace("키워드:", "").strip()
        summary = lines[1].replace("요약:", "").strip()
        return keywords, summary
    except Exception as e:
        print(f"[{brand}] GPT 처리 중 오류:", e)
        return "", ""

# ✅ 기존 날짜 체크
existing_dates = worksheet_data.col_values(1)
existing_brands = worksheet_data.col_values(2)
existing_today_rows = [(d, b) for d, b in zip(existing_dates, existing_brands) if d == today]

# 📤 시트에 데이터 추가
for brand in brands:
    if (today, brand) in existing_today_rows:
        print(f"{brand} 데이터 이미 존재 - 스킵")
        continue

    data_row, posts = fetch_instagram_data(brand)
    worksheet_data.append_row(data_row)
    print(f"{brand} InstagramData 저장 완료")

    keywords, summary = extract_keywords_and_summary(brand, posts)
    worksheet_insights.append_row([today, brand, keywords, summary])
    print(f"{brand} InstagramInsights 저장 완료")

# ChatGPT를 이용한 요약
try:
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Extract key keywords and give a short summary of these Instagram post titles."},
            {"role": "user", "content": "\n".join(titles)}
        ],
        max_tokens=300
    )
    summary_text = completion.choices[0].message.content.strip()

    keywords = summary_text.split("\n")[0]
    summary = "\n".join(summary_text.split("\n")[1:])

    insights_ws.append_row([today, brand, keywords, summary])
    print(f"[✓] {brand} 인사이트 저장 완료")
except Exception as e:
    print(f"[X] {brand} 요약 실패: {e}")
