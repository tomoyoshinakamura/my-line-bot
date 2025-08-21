import os
from flask import Flask, request, abort
from bs4 import BeautifulSoup
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from playwright.sync_api import sync_playwright

# 環境変数
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN").strip()
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET").strip()

app = Flask(__name__)
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 商品検索関数
def fetch_price(keyword: str) -> str:
    search_url = f"https://www.x-jpn.co.jp/?s={keyword}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(search_url, timeout=30000)

            # 商品一覧を取得
            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        item = soup.select_one("list-item__result__price")  # CSSセレクタを実際のサイトに合わせて調整
        if item:
            return f"「{keyword}」の買取価格: {item.text.strip()}"
        else:
            return f"「{keyword}」の商品は見つかりませんでした。"
    except Exception as e:
        return f"検索中にエラーが発生しました: {e}"

# LINE Webhook
@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

# メッセージ受信処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    keyword = event.message.text.strip()
    price_info = fetch_price(keyword)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=price_info))

# Render起動用
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
