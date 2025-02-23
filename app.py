from flask import Flask, jsonify
import requests
import json
import asyncio
import aiohttp
from newspaper import Article
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

app = Flask(__name__)
GOOGLE_NEWS_URL = "https://news.google.com/topstories?hl=en-IN&gl=IN&ceid=IN:en"
MAKE_WEBHOOK_URL = "https://hook.us2.make.com/23sypme7snydp7o8uopngmigqjxo78uy"

async def fetch_html(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        html = await page.content()
        await browser.close()
        return html

def parse_google_news(html):
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.select("article a[href]")
    news_items = []
    
    for article in articles[:10]:
        headline = article.get_text(strip=True)  # Strip extra spaces
        if not headline:
            headline = "Untitled News"  # Fallback if no text is found
        
        link = "https://news.google.com" + article["href"].replace("./", "/")
        news_items.append({"headline": headline, "link": link})
    
    return news_items


def extract_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print(f"❌ Failed to extract text from {url}: {e}")
        return None

def summarize_text(text):
    return " ".join(text.split()[:50]) + "..."  # Simple summary (first 50 words)

async def send_to_make(news_item):
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(MAKE_WEBHOOK_URL, headers=headers, json=news_item) as response:
                response_text = await response.text()
                print(f"📡 Response from Make.com: {response.status} - {response_text}")
        except Exception as e:
            print(f"❌ Exception while sending data: {e}")

async def get_news_data():
    html = await fetch_html(GOOGLE_NEWS_URL)
    news_items = parse_google_news(html)
    news_data = []
    for item in news_items:
        print(f"📰 Processing: {item['headline']}")
        article_text = extract_article_text(item['link'])
        summary = summarize_text(article_text) if article_text else "Could not extract article text."
        news_item = {"headline": item['headline'], "link": item['link'], "summary": summary}
        news_data.append(news_item)
        await send_to_make(news_item)
    return news_data

@app.route("/news", methods=["GET"])
def fetch_news():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    news_data = loop.run_until_complete(get_news_data())
    return jsonify(news_data)

if __name__ == "__main__":
    app.run(debug=True)
