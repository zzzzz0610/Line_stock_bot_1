# Line Stock Bot

一個整合股票和加密貨幣查詢功能的 LINE 機器人。

## 功能
### 股票查詢
- `/股票 2330` - 查詢台積電股票資訊
- `/股票 台積電` - 使用股票名稱查詢
- `/排行 漲幅` - 查看漲幅排行
- `/排行 跌幅` - 查看跌幅排行
- `/篩選 高殖利率` - 篩選高殖利率股票
- `/篩選 低本益比` - 篩選低本益比股票

### 加密貨幣查詢
- `/crypto btc` 或 `/加密 比特幣` - 查詢比特幣價格
- `/crypto eth` 或 `/加密 以太幣` - 查詢以太幣價格
- `/crypto bnb` 或 `/加密 幣安幣` - 查詢幣安幣價格
- `/crypto sol` 或 `/加密 索拉納` - 查詢索拉納價格

### 支援的加密貨幣
- BTC/比特幣/Bitcoin
- ETH/以太幣/Ethereum
- USDT/泰達幣/Tether
- BNB/幣安幣/Binance Coin
- SOL/索拉納/Solana

## 安裝與部署
1. 安裝依賴：`pip install -r requirements.txt`
2. 設置環境變數：
   - LINE_CHANNEL_SECRET
   - LINE_CHANNEL_ACCESS_TOKEN
3. 運行應用：`python app.py`

## 注意事項
- 股票資訊更新頻率為即時
- 加密貨幣價格每分鐘更新一次
- 如遇到查詢失敗，請稍後再試
