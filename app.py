from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime
import logging

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 股票代號和名稱的對應表
def get_stock_map():
    try:
        url = "https://tw.quote.finance.yahoo.net/quote/q?type=ta&perd=d&mkt=10&sym="
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        
        stock_map = {}
        # 直接使用股票代號作為key和value
        stock_map[data['id']] = data['id']
        return stock_map
    except Exception as e:
        print(f"Error getting stock map: {str(e)}")
        return {}

def get_stock_info(stock_id):
    try:
        # 使用另一個更穩定的 API
        url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{stock_id}.tw"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        
        if 'msgArray' not in data or not data['msgArray']:
            return None
            
        stock_data = data['msgArray'][0]
        
        price = float(stock_data['z']) if stock_data['z'] != '-' else float(stock_data['y'])
        change = price - float(stock_data['y'])
        change_percent = (change / float(stock_data['y'])) * 100
        
        return {
            'name': stock_data['n'],
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'volume': int(float(stock_data['v']) * 1000),
            'high': float(stock_data['h']),
            'low': float(stock_data['l']),
            'open': float(stock_data['o']),
            'prev_close': float(stock_data['y']),
            'update_time': stock_data['t']
        }
    except Exception as e:
        print(f"Error getting stock info: {str(e)}")
        return None

def get_stock_name(stock_id):
    try:
        url = f"https://tw.quote.finance.yahoo.net/quote/q?type=ta&perd=d&mkt=10&sym={stock_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers)
        data = json.loads(response.text)
        return data.get('n', stock_id)  # 如果找不到名稱，返回股票代號
    except:
        return stock_id

def get_stock_filter(filter_type):
    try:
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?response=json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'data' not in data:
            return "無法獲取股票資訊"
            
        filtered_stocks = []
        for stock in data['data']:
            if filter_type == "殖利率" and float(stock[2].replace(',', '')) > 5:
                filtered_stocks.append(f"股票：{stock[0]} {stock[1]}\n殖利率：{stock[2]}%")
            elif filter_type == "低本益比" and float(stock[4].replace(',', '')) < 10:
                filtered_stocks.append(f"股票：{stock[0]} {stock[1]}\nPE：{stock[4]}")
                
        return "\n\n".join(filtered_stocks[:5])  # 只返回前5個結果
    except Exception as e:
        return f"篩選時發生錯誤：{str(e)}"

def get_stock_ranking(rank_type="漲幅"):
    try:
        # 使用 Yahoo 財經 API
        url = "https://tw.stock.yahoo.com/_td-stock/api/resource/StockServices.rank;exchange=TAI;order=desc;period=1D;sortBy=change_percent?bkt=&device=desktop&ecma=modern&feature=ecmaModern%2CmodernStocksHeader&intl=tw&lang=zh-Hant-TW&partner=none&prid=2h0h0r9h8v8os&region=TW&site=finance&tz=Asia%2FTaipei&ver=1.2.1841&returnMeta=true"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'data' not in data:
            return "無法獲取排行資訊"
            
        stocks = data['data']
        
        # 根據漲跌幅排序
        if rank_type == "跌幅":
            stocks.reverse()
            
        result = []
        for stock in stocks[:5]:  # 只取前5名
            result.append(
                f"股票：{stock['symbol']} {stock['name']}\n"
                f"現價：{stock['price']}\n"
                f"漲跌：{stock['change']:+.2f} ({stock['changePercent']:+.2f}%)"
            )
            
        if not result:
            return "目前無法取得排行資訊，請稍後再試"
            
        return "\n\n".join(result)
        
    except Exception as e:
        logger.error(f"獲取排行榜時發生錯誤：{str(e)}")
        return f"獲取排行榜時發生錯誤，請稍後再試"

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
    text = event.message.text.strip()
    command = text.upper()

    try:
        logger.info(f"收到訊息: {text}")

        # 處理股票查詢
        if command.startswith('/股票'):
            parts = text.split()
            if len(parts) < 2:
                message = "請輸入正確格式：/股票 2330 或 /股票 台積電"
            else:
                stock_id = parts[1]
                stock_info = get_stock_info(stock_id)
                if stock_info:
                    message = (
                        f"股票：{stock_info['name']} ({stock_id})\n"
                        f"現價：{stock_info['price']}\n"
                        f"漲跌：{stock_info['change']:+.2f} ({stock_info['change_percent']:+.2f}%)\n"
                        f"成交量：{stock_info['volume']:,}\n"
                        f"最高：{stock_info['high']}\n"
                        f"最低：{stock_info['low']}\n"
                        f"開盤：{stock_info['open']}\n"
                        f"昨收：{stock_info['prev_close']}\n"
                        f"更新時間：{stock_info['update_time']}"
                    )
                else:
                    message = f"無法獲取股票 {stock_id} 的資訊"

        # 處理排行榜
        elif command.startswith('/排行'):
            parts = text.split()
            if len(parts) < 2:
                message = "請輸入正確格式：/排行 漲幅 或 /排行 跌幅"
            else:
                rank_type = parts[1]
                message = get_stock_ranking(rank_type)

        # 處理說明指令
        elif command == '/說明' or command == '/HELP':
            message = (
                "📈 股票查詢指令：\n"
                "/股票 2330 - 查詢股票即時資訊\n"
                "/股票 台積電 - 使用股票名稱查詢\n"
                "/排行 漲幅 - 查看漲幅排行\n"
                "/排行 跌幅 - 查看跌幅排行"
            )
        else:
            message = (
                "無效的指令！請使用以下指令：\n"
                "/股票 [代號] - 查詢股票\n"
                "/排行 [漲幅/跌幅] - 查看排行\n"
                "/說明 - 顯示完整指令說明"
            )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=message)
        )

    except Exception as e:
        logger.error(f"處理訊息時發生錯誤：{str(e)}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="系統發生錯誤，請稍後再試")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
