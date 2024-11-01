from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import json
from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

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
    try:
        text = event.message.text.strip().lower()
        
        if text.isdigit():
            stock_info = get_stock_info(text)
            if stock_info:
                change_symbol = "▲" if stock_info['change'] > 0 else "▼" if stock_info['change'] < 0 else "－"
                response_message = (
                    f"股票代號：{text}\n"
                    f"股票名稱：{stock_info['name']}\n"
                    f"即時股價：{stock_info['price']:.2f}\n"
                    f"漲跌：{change_symbol}{abs(stock_info['change']):.2f}"
                    f"（{stock_info['change_percent']:.2f}%）\n"
                    f"昨收：{stock_info['prev_close']:.2f}\n"
                    f"開盤：{stock_info['open']:.2f}\n"
                    f"最高：{stock_info['high']:.2f}\n"
                    f"最低：{stock_info['low']:.2f}\n"
                    f"成交量：{stock_info['volume']:,}\n"
                    f"更新時間：{stock_info['update_time']}"
                )
            else:
                response_message = f"無法獲取股票 {text} 的資訊，請確認代號是否正確"
        elif text in CRYPTO_MAP:
            crypto_info = get_crypto_info(CRYPTO_MAP[text])
            if crypto_info:
                change_symbol = "▲" if crypto_info['usd_24h_change'] > 0 else "▼" if crypto_info['usd_24h_change'] < 0 else "－"
                response_message = (
                    f"虛擬貨幣：{text.upper()}\n"
                    f"USD價格：${crypto_info['usd_price']:,.2f}\n"
                    f"TWD價格：NT${crypto_info['twd_price']:,.2f}\n"
                    f"24小時漲跌：{change_symbol}{abs(crypto_info['usd_24h_change']):.2f}%\n"
                    f"更新時間：{crypto_info['last_updated']}"
                )
            else:
                response_message = f"無法獲取 {text.upper()} 的資訊，請稍後再試"
        else:
            response_message = (
                "股票及虛擬貨幣查詢機器人使用說明：\n\n"
                "1. 股票查詢：\n"
                "• 直接輸入股票代號\n"
                "• 例如：2330\n"
                "• 顯示：即時股價、漲跌幅、開高低收、成交量\n\n"
                "2. 虛擬貨幣查詢：\n"
                "• 輸入代號或中文名稱\n"
                "• BTC 或 比特幣\n"
                "• ETH 或 以太幣\n"
                "• USDT 或 泰達幣\n"
                "• BNB 或 幣安幣\n"
                "• SOL 或 索拉納\n"
                "• 顯示：USD/TWD 價格、24h漲跌\n\n"
                "圖文選單：\n"
                "• 左：股票範例(2330)\n"
                "• 右：使用說明\n\n"
                "資料來源：\n"
                "• 股票：Yahoo財經\n"
                "• 虛擬貨幣：CoinGecko"
            )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response_message)
        )
    except Exception as e:
        response_message = "系統發生錯誤，請稍後再試"
        print(f"Error in handle_message: {str(e)}")

if __name__ == "__main__":
    app.run()
