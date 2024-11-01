from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

def get_stock_info(stock_id):
    try:
        # 使用 Yahoo 財經 API
        url = f"https://tw.quote.finance.yahoo.net/quote/q?type=ta&perd=d&mkt=10&sym={stock_id}"
        response = requests.get(url)
        data = json.loads(response.text)
        
        if 'ta' not in data or not data['ta']:
            return None
            
        # 解析股票資訊
        latest_data = data['ta'][0]
        price = float(latest_data[-1])  # 當前價格
        change = float(latest_data[-2])  # 漲跌
        volume = int(latest_data[-3])    # 成交量
        high = float(latest_data[-4])    # 最高
        low = float(latest_data[-5])     # 最低
        open_price = float(latest_data[-6]) # 開盤
        
        # 計算漲跌幅
        prev_price = price - change
        change_percent = (change / prev_price) * 100 if prev_price != 0 else 0
        
        return {
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'volume': volume,
            'high': high,
            'low': low,
            'open': open_price
        }
    except Exception as e:
        print(f"Error getting stock info: {str(e)}")
        return None

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text
    
    if text.startswith('/股票'):
        try:
            stock_id = text.split()[1]
            stock_info = get_stock_info(stock_id)
            
            if stock_info:
                change_symbol = "▲" if stock_info['change'] > 0 else "▼" if stock_info['change'] < 0 else "－"
                response_message = (
                    f"股票代號：{stock_id}\n"
                    f"當前價格：{stock_info['price']:.2f}\n"
                    f"漲跌：{change_symbol}{abs(stock_info['change']):.2f}"
                    f"（{stock_info['change_percent']:.2f}%）\n"
                    f"開盤：{stock_info['open']:.2f}\n"
                    f"最高：{stock_info['high']:.2f}\n"
                    f"最低：{stock_info['low']:.2f}\n"
                    f"成交量：{stock_info['volume']:,}"
                )
            else:
                response_message = "無法獲取股票資訊，請確認股票代號是否正確"
        except Exception as e:
            response_message = f"發生錯誤：{str(e)}"
    else:
        response_message = "請使用 /股票 加上股票代號來查詢，例如：/股票 2330"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_message)
    )

if __name__ == "__main__":
    app.run()
