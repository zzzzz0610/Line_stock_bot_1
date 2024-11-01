from functools import wraps
import time
import logging

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries=3, delay_seconds=1):
    """
    重試裝飾器，用於處理可能失敗的操作
    
    參數:
        max_retries (int): 最大重試次數
        delay_seconds (int): 重試之間的延遲時間（秒）
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_exception = None
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    retries += 1
                    logger.warning(
                        f"執行 {func.__name__} 失敗 (嘗試 {retries}/{max_retries}): {str(e)}"
                    )
                    
                    if retries < max_retries:
                        time.sleep(delay_seconds)
                    
            logger.error(
                f"{func.__name__} 在 {max_retries} 次嘗試後失敗: {str(last_exception)}"
            )
            raise last_exception
            
        return wrapper
    return decorator
