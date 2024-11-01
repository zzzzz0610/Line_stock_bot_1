def get_stock_info(stock_id):
    try:
        # 使用 Yahoo 財經 API
        url = f"https://tw.quote.finance.yahoo.net/quote/q?type=ta&perd=d&mkt=10&sym={stock_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        
        response = requests.get(url, headers=headers)
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
            'open': open_price,
            'name': get_stock_name(stock_id)  # 獲取股票名稱
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
