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
        # 使用 twstock API
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_id}.tw"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        
        if 'msgArray' not in data or not data['msgArray']:
            return None
            
        stock_data = data['msgArray'][0]
        
        # 解析股票資訊
        price = float(stock_data['z']) if stock_data['z'] != '-' else float(stock_data['y'])  # 當前價格或昨收價
        yesterday_price = float(stock_data['y'])    # 昨收價
        change = price - yesterday_price            # 漲跌
        change_percent = (change / yesterday_price * 100) if yesterday_price != 0 else 0
        volume = int(float(stock_data['v']) * 1000) if stock_data['v'] != '-' else 0  # 成交量
        high = float(stock_data['h']) if stock_data['h'] != '-' else price    # 最高
        low = float(stock_data['l']) if stock_data['l'] != '-' else price     # 最低
        open_price = float(stock_data['o']) if stock_data['o'] != '-' else price  # 開盤
        
        return {
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'volume': volume,
            'high': high,
            'low': low,
            'open': open_price,
            'name': stock_data['n']  # 股票名稱
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
                    f"股票名稱：{stock_info['name']}\n"
                    f"當前價格：{stock_info['price']:.2f}\n"
                    f"漲跌：{change_symbol}{abs(stock_info['change']):.2f}"
                    f"（{stock_info['change_percent']:.2f}%）\n"
                    f"開盤：{stock_info['open']:.2f}\n"
                    f"最高：{stock_info['high']:.2f}\n"
                    f"最低：{stock_info['low']:.2f}\n"
                    f"成交量：{stock_info['volume']:,}"
                )
            else:
                response_message = "無法獲取股票資訊，請確認股票代號是否正確\n範例：/股票 2330"
        except Exception as e:
            response_message = f"發生錯誤：{str(e)}\n請確認股票代號是否正確\n範例：/股票 2330"
    else:
        response_message = "請使用 /股票 加上股票代號來查詢\n範例：/股票 2330"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_message)
    )

if __name__ == "__main__":
    app.run()
