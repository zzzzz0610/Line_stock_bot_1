from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import yfinance as yf
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

def get_stock_info(stock_id):
    try:
        stock = yf.Ticker(f"{stock_id}.TW")
        info = stock.info
        current_price = info.get('regularMarketPrice', '無法獲取')
        change = info.get('regularMarketChange', 0)
        change_percent = info.get('regularMarketChangePercent', 0)
        volume = info.get('regularMarketVolume', 0)
        
        return {
            'price': current_price,
            'change': change,
            'change_percent': change_percent,
            'volume': volume
        }
    except:
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
                    f"當前價格：{stock_info['price']}\n"
                    f"漲跌：{change_symbol}{abs(stock_info['change']):.2f}"
                    f"（{stock_info['change_percent']:.2f}%）\n"
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