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
from services.crypto_service import CryptoService

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
            if filter_type == "高殖利率" and float(stock[2].replace(',', '')) > 5:
                filtered_stocks.append(f"股票：{stock[0]} {stock[1]}\n殖利率：{stock[2]}%")
            elif filter_type == "低本益比" and float(stock[4].replace(',', '')) < 10:
                filtered_stocks.append(f"股票：{stock[0]} {stock[1]}\nPE：{stock[4]}")
                
        return "\n\n".join(filtered_stocks[:5])  # 只返回前5個結果
    except Exception as e:
        return f"篩選時發生錯誤：{str(e)}"

def get_stock_ranking(rank_type="漲幅"):
    try:
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?response=json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        stocks = []
        for stock in data['data']:
            try:
                change_percent = float(stock[7].replace('%', ''))
                stocks.append({
                    'code': stock[0],
                    'name': stock[1],
                    'change': change_percent
                })
            except:
                continue
                
        # 根據漲跌幅排序
        if rank_type == "漲幅":
            stocks.sort(key=lambda x: x['change'], reverse=True)
        else:
            stocks.sort(key=lambda x: x['change'])
            
        result = []
        for stock in stocks[:5]:
            result.append(
                f"股票：{stock['code']} {stock['name']}\n"
                f"漲跌幅：{stock['change']}%"
            )
            
        return "\n\n".join(result)
    except Exception as e:
        return f"獲取排行榜時發生錯誤：{str(e)}"

def get_crypto_info(crypto_id):
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': crypto_id,
            'vs_currencies': 'usd,twd',
            'include_24hr_change': 'true',
            'include_last_updated_at': 'true'
        }
        
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"API error: {response.status_code}")
            return None
            
        data = response.json()
        if crypto_id not in data:
            return None
            
        crypto_data = data[crypto_id]
        return {
            'usd_price': crypto_data['usd'],
            'twd_price': crypto_data['twd'],
            'usd_24h_change': crypto_data.get('usd_24h_change', 0),
            'last_updated': datetime.fromtimestamp(crypto_data['last_updated_at']).strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"Error getting crypto info: {str(e)}")
        return None

# 虛擬貨幣代號對應表
CRYPTO_MAP = {
    'btc': 'bitcoin',
    'bitcoin': 'bitcoin',
    '比特幣': 'bitcoin',
    'eth': 'ethereum',
    'ethereum': 'ethereum',
    '以太幣': 'ethereum',
    'usdt': 'tether',
    'tether': 'tether',
    '泰達幣': 'tether',
    'bnb': 'binancecoin',
    'binance': 'binancecoin',
    '幣安幣': 'binancecoin',
    'sol': 'solana',
    'solana': 'solana',
    '索拉納': 'solana'
}

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
    text = event.message.text.strip().upper()
    
    if text.startswith('/CRYPTO') or text.startswith('/加密'):
        try:
            # 解析請求
            parts = text.split()
            if len(parts) < 2:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text="請輸入正確格式：/crypto BTC 或 /加密 BTC")
                )
                return
            
            # 獲取幣種符號
            symbol = parts[1].lower()  # 轉換為小寫
            
            # 檢查是否在支援的幣種映射中
            if symbol in CRYPTO_MAP:
                symbol = CRYPTO_MAP[symbol]
            
            # 創建服務實例
            crypto_service = CryptoService()
            price_info = crypto_service.get_crypto_price(symbol)
            
            if price_info:
                message = (
                    f"📊 {symbol.upper()}/USDT 即時報價\n\n"
                    f"現價: ${price_info['price']:,.2f}\n"
                    f"24h高: ${price_info['high']:,.2f}\n"
                    f"24h低: ${price_info['low']:,.2f}\n"
                    f"漲跌: {price_info['change']:+.2f}%\n"
                    f"成交量: {price_info['volume']:,.2f}\n"
                    f"更新時間: {price_info['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}"
                )
            else:
                # 嘗試使用備用 API
                backup_info = crypto_service.get_crypto_price_backup(symbol)
                if backup_info:
                    message = (
                        f"📊 {symbol.upper()}/USDT 即時報價\n\n"
                        f"現價: ${backup_info['price']:,.2f}\n"
                        f"24h漲跌: {backup_info['change']:+.2f}%"
                    )
                else:
                    message = f"無法獲取 {symbol.upper()} 的價格資訊"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=message)
            )
            
        except Exception as e:
            logger.error(f"處理加密貨幣查詢時發生錯誤：{str(e)}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="系統錯誤，請稍後再試")
            )

if __name__ == "__main__":
    app.run()
