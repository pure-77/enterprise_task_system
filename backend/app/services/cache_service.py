import time
from typing import Optional
from app.db.redis_client import get_redis
from app.core.config import settings


class CacheService:
    """缓存服务类 - 面试考点：使用Redis缓存验证码，提高性能"""
    
    @staticmethod
    def set_verify_code(email: str, code: str, expire_seconds: int = None) -> bool:
        """设置验证码 - 面试考点：Redis存储验证码，设置过期时间"""
        if expire_seconds is None:
            expire_seconds = settings.VERIFY_CODE_EXPIRE_SECONDS
        
        key = f"verify_code:{email}"
        try:
            result = get_redis().setex(key, expire_seconds, code)
            print(f"设置验证码成功: {email} -> {code}, key: {key}, result: {result}")
            return True
        except Exception as e:
            print(f"设置验证码失败: {e}")
            return False
    
    @staticmethod
    def get_verify_code(email: str) -> Optional[str]:
        """获取验证码 - 面试考点：从Redis读取验证码"""
        key = f"verify_code:{email}"
        print(f"尝试获取验证码，email: {email}, key: {key}")
        try:
            code = get_redis().get(key)
            print(f"Redis返回的验证码: {code}")
            return code
        except Exception as e:
            print(f"获取验证码失败: {e}")
            # 开发环境下，为了方便测试，返回固定验证码
            if settings.DEBUG:
                print("DEBUG模式：返回固定验证码 '123456'")
                return "123456"
            return None
    
    @staticmethod
    def delete_verify_code(email: str) -> bool:
        """删除验证码 - 面试考点：验证码使用后删除"""
        key = f"verify_code:{email}"
        try:
            get_redis().delete(key)
            return True
        except Exception as e:
            print(f"删除验证码失败: {e}")
            return False
    
    @staticmethod
    def set_send_time(email: str, timestamp: int = None) -> bool:
        """设置发送时间 - 面试考点：记录验证码发送时间，用于防刷"""
        if timestamp is None:
            timestamp = int(time.time())
        
        key = f"verify_code_time:{email}"
        try:
            get_redis().setex(key, settings.VERIFY_CODE_SEND_INTERVAL, str(timestamp))
            return True
        except Exception as e:
            print(f"设置发送时间失败: {e}")
            return False
    
    @staticmethod
    def get_send_time(email: str) -> Optional[int]:
        """获取发送时间 - 面试考点：检查上次发送时间"""
        key = f"verify_code_time:{email}"
        try:
            time_str = get_redis().get(key)
            return int(time_str) if time_str else None
        except Exception as e:
            print(f"获取发送时间失败: {e}")
            # 开发环境下，为了方便测试，返回None
            if settings.DEBUG:
                return None
            return None
    
    @staticmethod
    def can_send_verify_code(email: str) -> bool:
        """检查是否可以发送验证码 - 面试考点：防刷机制"""
        last_send_time = CacheService.get_send_time(email)
        if last_send_time is None:
            return True
        
        current_time = int(time.time())
        time_diff = current_time - last_send_time
        return time_diff >= settings.VERIFY_CODE_SEND_INTERVAL
    
    @staticmethod
    def get_remaining_time(email: str) -> int:
        """获取剩余等待时间 - 面试考点：用于前端倒计时"""
        last_send_time = CacheService.get_send_time(email)
        if last_send_time is None:
            return 0
        
        current_time = int(time.time())
        time_diff = current_time - last_send_time
        remaining = settings.VERIFY_CODE_SEND_INTERVAL - time_diff
        return max(0, remaining)
    
    @staticmethod
    def set_refresh_token(user_id: int, refresh_token: str) -> bool:
        """存储刷新令牌 - 面试考点：Redis存储刷新令牌，设置7天过期"""
        key = f"refresh_token:{user_id}"
        try:
            # 设置7天过期时间
            get_redis().setex(key, 7 * 24 * 60 * 60, refresh_token)
            print(f"存储刷新令牌成功: user_id={user_id}, key={key}")
            return True
        except Exception as e:
            print(f"存储刷新令牌失败: {e}")
            return False
    
    @staticmethod
    def get_refresh_token(user_id: int) -> Optional[str]:
        """获取刷新令牌 - 面试考点：从Redis读取刷新令牌"""
        key = f"refresh_token:{user_id}"
        try:
            token = get_redis().get(key)
            return token
        except Exception as e:
            print(f"获取刷新令牌失败: {e}")
            return None
    
    @staticmethod
    def delete_refresh_token(user_id: int) -> bool:
        """删除刷新令牌 - 面试考点：用户登出时删除刷新令牌"""
        key = f"refresh_token:{user_id}"
        try:
            get_redis().delete(key)
            print(f"删除刷新令牌成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"删除刷新令牌失败: {e}")
            return False

    @staticmethod
    def is_refresh_token_used(user_id: int, token_hash: str) -> bool:
        """检查刷新令牌是否已被使用过 - 用于检测令牌重放攻击"""
        key = f"used_refresh_token:{user_id}:{token_hash}"
        try:
            return get_redis().exists(key) > 0
        except Exception as e:
            print(f"检查刷新令牌使用状态失败: {e}")
            return False

    @staticmethod
    def mark_refresh_token_used(user_id: int, token_hash: str) -> bool:
        """标记刷新令牌为已使用 - 设置与刷新令牌相同的过期时间"""
        key = f"used_refresh_token:{user_id}:{token_hash}"
        try:
            get_redis().setex(key, settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, "1")
            return True
        except Exception as e:
            print(f"标记刷新令牌已使用失败: {e}")
            return False
    
    @staticmethod
    def set_user_categories(user_id: int, categories: list) -> bool:
        """设置用户分类列表缓存 - 面试考点：Redis缓存优化"""
        import json
        key = f"user_categories:{user_id}"
        try:
            # 设置5分钟过期时间
            get_redis().setex(key, 5 * 60, json.dumps(categories, default=str))
            print(f"设置用户分类缓存成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"设置用户分类缓存失败: {e}")
            return False
    
    @staticmethod
    def get_user_categories(user_id: int) -> Optional[list]:
        """获取用户分类列表缓存 - 面试考点：Redis缓存优化"""
        import json
        key = f"user_categories:{user_id}"
        try:
            data = get_redis().get(key)
            if data:
                categories = json.loads(data)
                print(f"获取用户分类缓存成功: user_id={user_id}")
                return categories
            return None
        except Exception as e:
            print(f"获取用户分类缓存失败: {e}")
            return None
    
    @staticmethod
    def delete_user_categories(user_id: int) -> bool:
        """删除用户分类列表缓存 - 面试考点：缓存一致性"""
        key = f"user_categories:{user_id}"
        try:
            get_redis().delete(key)
            print(f"删除用户分类缓存成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"删除用户分类缓存失败: {e}")
            return False
    
    @staticmethod
    def set_user_tasks(user_id: int, tasks: list) -> bool:
        """设置用户任务列表缓存 - 面试考点：Redis缓存优化"""
        import json
        key = f"user_tasks:{user_id}"
        try:
            # 设置5分钟过期时间
            get_redis().setex(key, 5 * 60, json.dumps(tasks, default=str))
            print(f"设置用户任务缓存成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"设置用户任务缓存失败: {e}")
            return False
    
    @staticmethod
    def get_user_tasks(user_id: int) -> Optional[list]:
        """获取用户任务列表缓存 - 面试考点：Redis缓存优化"""
        import json
        key = f"user_tasks:{user_id}"
        try:
            data = get_redis().get(key)
            if data:
                tasks = json.loads(data)
                print(f"获取用户任务缓存成功: user_id={user_id}")
                return tasks
            return None
        except Exception as e:
            print(f"获取用户任务缓存失败: {e}")
            return None
    
    @staticmethod
    def delete_user_tasks(user_id: int) -> bool:
        """删除用户任务列表缓存 - 面试考点：缓存一致性"""
        key = f"user_tasks:{user_id}"
        try:
            get_redis().delete(key)
            print(f"删除用户任务缓存成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"删除用户任务缓存失败: {e}")
            return False
    
    @staticmethod
    def delete_user_info(user_id: int) -> bool:
        """删除用户信息缓存 - 面试考点：保持缓存一致性"""
        key = f"user_info:{user_id}"
        try:
            get_redis().delete(key)
            print(f"删除用户信息缓存成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"删除用户信息缓存失败: {e}")
            return False
    
    @staticmethod
    def set_email_change(user_id: int, email: str, code: str) -> bool:
        """设置邮箱修改信息 - 面试考点：临时存储邮箱修改信息"""
        key = f"email_change:{user_id}"
        try:
            import json
            data = {"email": email, "code": code}
            get_redis().setex(key, 600, json.dumps(data))  # 10分钟过期
            print(f"设置邮箱修改信息成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"设置邮箱修改信息失败: {e}")
            return False
    
    @staticmethod
    def get_email_change(user_id: int) -> Optional[dict]:
        """获取邮箱修改信息 - 面试考点：读取临时存储信息"""
        key = f"email_change:{user_id}"
        try:
            import json
            data = get_redis().get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"获取邮箱修改信息失败: {e}")
            return None
    
    @staticmethod
    def delete_email_change(user_id: int) -> bool:
        """删除邮箱修改信息 - 面试考点：清理临时数据"""
        key = f"email_change:{user_id}"
        try:
            get_redis().delete(key)
            print(f"删除邮箱修改信息成功: user_id={user_id}")
            return True
        except Exception as e:
            print(f"删除邮箱修改信息失败: {e}")
            return False
    
    @staticmethod
    def set_password_reset(email: str, code: str, user_id: int) -> bool:
        """设置密码重置信息 - 面试考点：临时存储密码重置信息"""
        key = f"password_reset:{email}"
        try:
            import json
            data = {"code": code, "user_id": user_id}
            get_redis().setex(key, 600, json.dumps(data))  # 10分钟过期
            print(f"设置密码重置信息成功: email={email}")
            return True
        except Exception as e:
            print(f"设置密码重置信息失败: {e}")
            return False
    
    @staticmethod
    def get_password_reset(email: str) -> Optional[dict]:
        """获取密码重置信息 - 面试考点：读取临时存储信息"""
        key = f"password_reset:{email}"
        try:
            import json
            data = get_redis().get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"获取密码重置信息失败: {e}")
            return None
    
    @staticmethod
    def delete_password_reset(email: str) -> bool:
        """删除密码重置信息 - 面试考点：清理临时数据"""
        key = f"password_reset:{email}"
        try:
            get_redis().delete(key)
            print(f"删除密码重置信息成功: email={email}")
            return True
        except Exception as e:
            print(f"删除密码重置信息失败: {e}")
            return False


cache_service = CacheService()
