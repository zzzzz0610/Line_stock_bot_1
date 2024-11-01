import ccxt
import requests
from datetime import datetime
import time

class CryptoService:
    def __init__(self):
        # 使用 ccxt 庫來獲取加密貨幣資訊
        self.exchange = ccxt.binance({
            'enableRateLimit': True,  # 啟用請求限制
            'timeout': 30000,  # 設置超時時間
        })
        
        self.backup_apis = {
            'coingecko': 'https://api.coingecko.com/api/v3',
            'cryptocompare': 'https://min-api.cryptocompare.com/data'
        }
        
    def get_crypto_price(self, symbol):
        try:
            # 確保 symbol 格式正確（例如：'BTC/USDT'）
            if '/' not in symbol:
                symbol = f'{symbol}/USDT'
            
            # 獲取即時價格
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'price': ticker['last'],
                'high': ticker['high'],
                'low': ticker['low'],
                'volume': ticker['baseVolume'],
                'change': ticker['percentage'],
                'timestamp': datetime.fromtimestamp(ticker['timestamp']/1000)
            }
            
        except ccxt.NetworkError as e:
            logger.error(f"網路錯誤：{str(e)}")
            return None
        except ccxt.ExchangeError as e:
            logger.error(f"交易所錯誤：{str(e)}")
            return None
        except Exception as e:
            logger.error(f"獲取加密貨幣價格時發生錯誤：{str(e)}")
            return None 

    def get_crypto_price_backup(self, symbol):
        """使用備用 API 獲取價格"""
        try:
            # 嘗試使用 CoinGecko API
            url = f"{self.backup_apis['coingecko']}/simple/price"
            params = {
                'ids': symbol.lower(),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    'price': data[symbol.lower()]['usd'],
                    'change': data[symbol.lower()]['usd_24h_change']
                }
                
        except Exception as e:
            logger.error(f"備用 API 請求失敗：{str(e)}")
            return None 
