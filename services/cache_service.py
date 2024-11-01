import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """
    簡單的記憶體快取服務
    """
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    def get(self, key: str):
        """
        從快取中獲取值
        
        參數:
            key (str): 快取鍵
            
        返回:
            快取的值或 None（如果不存在或已過期）
        """
        try:
            if key not in self._cache:
                return None
                
            # 檢查是否過期
            if datetime.now() > self._expiry[key]:
                self.delete(key)
                return None
                
            return self._cache[key]
            
        except Exception as e:
            logger.error(f"從快取獲取數據時發生錯誤: {str(e)}")
            return None
    
    def set(self, key: str, value, expire_seconds: int = 60):
        """
        設置快取值
        
        參數:
            key (str): 快取鍵
            value: 要快取的值
            expire_seconds (int): 過期時間（秒）
        """
        try:
            self._cache[key] = value
            self._expiry[key] = datetime.now() + timedelta(seconds=expire_seconds)
            
        except Exception as e:
            logger.error(f"設置快取時發生錯誤: {str(e)}")
    
    def delete(self, key: str):
        """
        刪除快取項
        
        參數:
            key (str): 要刪除的快取鍵
        """
        try:
            if key in self._cache:
                del self._cache[key]
            if key in self._expiry:
                del self._expiry[key]
                
        except Exception as e:
            logger.error(f"刪除快取時發生錯誤: {str(e)}")
    
    def clear(self):
        """清空所有快取"""
        self._cache.clear()
        self._expiry.clear() 
