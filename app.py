from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import requests
import json
from dotenv import load_dotenv
import os
from bs4 import BeautifulSoup

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

def get_stock_news(stock_id):
    try:
        # 使用 Yahoo 財經新聞
        url = f"https://tw.stock.yahoo.com/quote/{stock_id}/news"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        news_items = soup.find_all('div', {'class': 'Mt(20px) Pos(r)'})
        
        if not news_items:
            return f"找不到 {stock_id} 的相關新聞"
        
        news_list = []
        for item in news_items[:5]:  # 取前5則新聞
            title = item.find('h3').text.strip()
            news_list.append(f"• {title}")
            
        return "\n\n".join(news_list)
    except Exception as e:
        print(f"Error getting news: {str(e)}")
        return f"獲取新聞時發生錯誤：{str(e)}"

def get_industry_analysis():
    try:
        # 使用台灣證交所API獲取產業資訊
        url = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d?response=json"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if 'data' not in data:
            return "無法獲取產業資訊"
        
        # 整理產業資訊
        industry_data = {}
        for item in data['data']:
            industry = item[2]  # 產業別
            pe = float(item[4]) if item[4] != '-' else 0  # 本益比
            dividend = float(item[2]) if item[2] != '-' else 0  # 殖利率
            
            if industry not in industry_data:
                industry_data[industry] = {
                    'count': 1,
                    'pe_sum': pe,
                    'dividend_sum': dividend
                }
            else:
                industry_data[industry]['count'] += 1
                industry_data[industry]['pe_sum'] += pe
                industry_data[industry]['dividend_sum'] += dividend
        
        # 計算平均值並排序
        analysis_result = []
        for industry, data in industry_data.items():
            avg_pe = data['pe_sum'] / data['count']
            avg_dividend = data['dividend_sum'] / data['count']
            analysis_result.append({
                'industry': industry,
                'avg_pe': avg_pe,
                'avg_dividend': avg_dividend,
                'count': data['count']
            })
        
        # 依照本益比排序
        analysis_result.sort(key=lambda x: x['avg_pe'])
        
        # 格式化輸出
        output = "產業類股分析：\n\n"
        for item in analysis_result[:8]:  # 顯示前8個產業
            output += (
                f"【{item['industry']}】\n"
                f"平均本益比：{item['avg_pe']:.2f}\n"
                f"平均殖利率：{item['avg_dividend']:.2f}%\n"
                f"成分股數：{item['count']}\n"
                f"-------------------\n"
            )
        
        return output
    except Exception as e:
        print(f"Error getting industry analysis: {str(e)}")
        return f"獲取產業分析時發生錯誤：{str(e)}"

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
    elif text.startswith('/新聞'):
        try:
            stock_id = text.split()[1]
            news = get_stock_news(stock_id)
            response_message = f"股票 {stock_id} 相關新聞：\n\n{news}"
        except IndexError:
            response_message = "請輸入正確的股票代號\n範例：/新聞 2330"
        except Exception as e:
            response_message = f"發生錯誤：{str(e)}"
    elif text.startswith('/產業'):
        response_message = get_industry_analysis()
    else:
        response_message = (
            "支援的指令：\n"
            "/股票 股票代號：查看股票資訊\n"
            "/新聞 股票代號：查看相關新聞\n"
            "/產業：查看產業類股分析\n"
            "範例：/股票 2330"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_message)
    )

if __name__ == "__main__":
    app.run()
