import ccxt
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class CryptoService:
    def __init__(self):
        try:
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'timeout': 30000,
            })
            self.backup_apis = {
                'coingecko': 'https://api.coingecko.com/api/v3',
                'cryptocompare': 'https://min-api.cryptocompare.com/data'
            }
        except Exception as e:
            logger.error(f"初始化 Binance API 時發生錯誤：{str(e)}")
            self.exchange = None
            
    def get_crypto_price(self, symbol):
        try:
            # 轉換符號格式
            if '/' not in symbol:
                symbol = f'{symbol.upper()}/USDT'
            
            if not self.exchange:
                return None
                
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'price': float(ticker['last']),
                'high': float(ticker['high']),
                'low': float(ticker['low']),
                'volume': float(ticker['baseVolume']),
                'change': float(ticker['percentage']),
                'timestamp': datetime.fromtimestamp(ticker['timestamp']/1000)
            }
            
        except Exception as e:
            logger.error(f"獲取加密貨幣 {symbol} 價格時發生錯誤：{str(e)}")
            return None

    def get_crypto_price_backup(self, symbol):
        """使用備用 API 獲取價格"""
        try:
            url = f"{self.backup_apis['coingecko']}/simple/price"
            params = {
                'ids': symbol.lower(),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if symbol.lower() in data:
                    return {
                        'price': data[symbol.lower()]['usd'],
                        'change': data[symbol.lower()].get('usd_24h_change', 0)
                    }
            return None
                
        except Exception as e:
            logger.error(f"備用 API 請求失敗：{str(e)}")
            return None
