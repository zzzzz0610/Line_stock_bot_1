# Line Stock Bot

一個整合台股查詢功能的 LINE 機器人。

## 功能
### 股票查詢
- `/股票 2330` - 查詢台積電股票資訊
- `/股票 台積電` - 使用股票名稱查詢
- `/排行 漲幅` - 查看漲幅排行
- `/排行 跌幅` - 查看跌幅排行

## 安裝與部署
1. 安裝依賴：`pip install -r requirements.txt`
2. 設置環境變數：
   - LINE_CHANNEL_SECRET
   - LINE_CHANNEL_ACCESS_TOKEN
3. 運行應用：`python app.py`

## 注意事項
- 股票資訊更新頻率為即時
- 如遇到查詢失敗，請稍後再試
