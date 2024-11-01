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
        url = "https://www.twse.com.tw/rwd/zh/api/codeQuery"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        
        stock_map = {}
        for item in data.get('suggestions', []):
            if item:
                parts = item.split('\t')
                if len(parts) >= 2:
                    code = parts[0].strip()
                    name = parts[1].strip()
                    stock_map[name] = code
                    # 也可以用代號查詢
                    stock_map[code] = code
        return stock_map
    except Exception as e:
        print(f"Error getting stock map: {str(e)}")
        return {}

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
        # 使用 CoinGecko API
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': crypto_id,
            'vs_currencies': 'usd,twd',
            'include_24hr_change': 'true',
            'include_24hr_vol': 'true',
            'include_last_updated_at': 'true'
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        
        if crypto_id not in data:
            return None
            
        crypto_data = data[crypto_id]
        
        return {
            'usd_price': crypto_data['usd'],
            'twd_price': crypto_data['twd'],
            'usd_24h_change': crypto_data['usd_24h_change'],
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
    text = event.message.text.strip().lower()  # 轉換為小寫
    
    # 取得股票代號對應表
    stock_map = get_stock_map()
    
    # 檢查是否為虛擬貨幣查詢
    if text in CRYPTO_MAP:
        try:
            crypto_id = CRYPTO_MAP[text]
            crypto_info = get_crypto_info(crypto_id)
            
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
                response_message = "無法獲取虛擬貨幣資訊，請稍後再試"
        except Exception as e:
            response_message = f"發生錯誤：{str(e)}"
    elif text in stock_map:
        try:
            stock_id = stock_map[text]
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
                response_message = "無法獲取股票資訊，請確認股票代號是否正確\n範例：2330 或 台積電"
        except Exception as e:
            response_message = f"發生錯誤：{str(e)}\n請確認股票代號是否正確\n範例：2330 或 台積電"
    elif text in ['說明', 'help', '使用說明']:
        response_message = (
            "股票查詢機器人使用說明：\n\n"
            "1. 股票查詢：\n"
            "• 直接輸入股票代號或名稱\n"
            "• 例如：2330 或 台積電\n\n"
            "2. 股票篩選功能：\n"
            "• 輸入「高殖利率」：顯示殖利率>5%的股票\n"
            "• 輸入「低本益比」：顯示本益比<10的股票\n\n"
            "3. 漲跌排行：\n"
            "• 輸入「漲幅排行」：顯示今日漲幅前五名\n"
            "• 輸入「跌幅排行」：顯示今日跌幅前五名\n\n"
            "4. 虛擬貨幣查詢：\n"
            "• BTC/比特幣：比特幣即時價格\n"
            "• ETH/以太幣：以太坊即時價格\n"
            "• USDT/泰達幣：泰達幣即時價格\n"
            "• BNB/幣安幣：幣安幣即時價格\n"
            "• SOL/索拉納：索拉納即時價格\n\n"
            "圖文選單功能：\n"
            "• 左：股票範例(台積電)\n"
            "• 右：使用說明\n\n"
            "資料來源：台灣證券交易所、CoinGecko"
        )
    else:
        response_message = "請輸入正確的股票代號或股票名稱\n範例：2330 或 台積電"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_message)
    )

if __name__ == "__main__":
    app.run()
