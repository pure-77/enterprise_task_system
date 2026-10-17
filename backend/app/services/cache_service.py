import time
import json
import logging
from typing import Optional, Callable, Any
from app.db.redis_client import get_redis
from app.core.config import settings

logger = logging.getLogger("cache")


class CacheService:
    """缓存服务类 - 面试考点：使用Redis缓存，支持多域缓存与主动失效"""

    # ==================== 通用工具 ====================

    @staticmethod
    def _get(key: str) -> Optional[str]:
        """安全获取缓存值"""
        try:
            val = get_redis().get(key)
            if val is not None:
                logger.info(f"[CACHE HIT] GET key={key}")
            else:
                logger.info(f"[CACHE MISS] GET key={key}")
            return val
        except Exception as e:
            logger.warning(f"[CACHE ERROR] GET key={key} error={e}")
            return None

    @staticmethod
    def _set(key: str, value: str, ttl: int) -> bool:
        """安全设置缓存值"""
        try:
            get_redis().setex(key, ttl, value)
            logger.info(f"[CACHE SET] key={key} ttl={ttl}B len={len(value)}")
            return True
        except Exception as e:
            logger.warning(f"[CACHE ERROR] SET key={key} error={e}")
            return False

    @staticmethod
    def _delete(key: str) -> bool:
        """安全删除缓存"""
        try:
            get_redis().delete(key)
            logger.info(f"[CACHE DEL] key={key}")
            return True
        except Exception as e:
            logger.warning(f"[CACHE ERROR] DEL key={key} error={e}")
            return False

    @staticmethod
    def _get_json(key: str) -> Optional[Any]:
        """获取 JSON 缓存"""
        raw = CacheService._get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"[CACHE ERROR] JSON decode key={key} error={e}")
            return None

    @staticmethod
    def _set_json(key: str, value: Any, ttl: int) -> bool:
        """设置 JSON 缓存"""
        try:
            payload = json.dumps(value, default=str)
            return CacheService._set(key, payload, ttl)
        except Exception as e:
            logger.warning(f"[CACHE ERROR] JSON encode key={key} error={e}")
            return False

    @staticmethod
    def _invalidate_pattern(pattern: str) -> int:
        """按模式批量删除缓存（使用 SCAN + DEL 避免阻塞）"""
        deleted = 0
        try:
            redis = get_redis()
            cursor = 0
            while True:
                cursor, keys = redis.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += redis.delete(*keys)
                if cursor == 0:
                    break
            logger.info(f"[CACHE INVALIDATE] pattern={pattern} deleted={deleted}")
        except Exception as e:
            logger.warning(f"[CACHE ERROR] INVALIDATE pattern={pattern} error={e}")
        return deleted

    # ==================== 验证码缓存 ====================
    
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

    # ==================== 用户信息缓存（高频读取） ====================

    @staticmethod
    def set_user_info(user_id: int, info: dict) -> bool:
        """缓存用户基础信息（昵称、头像、角色等）"""
        key = f"user_info:{user_id}"
        result = CacheService._set_json(key, info, settings.USER_INFO_CACHE_TTL)
        logger.info(f"[CACHE USER] SET user_id={user_id} key={key} result={result}")
        return result

    @staticmethod
    def get_user_info(user_id: int) -> Optional[dict]:
        """获取用户信息缓存"""
        key = f"user_info:{user_id}"
        result = CacheService._get_json(key)
        if result is not None:
            logger.info(f"[CACHE USER] HIT user_id={user_id}")
        else:
            logger.info(f"[CACHE USER] MISS user_id={user_id}")
        return result

    @staticmethod
    def delete_user_info(user_id: int) -> bool:
        """删除用户信息缓存（资料更新时调用）"""
        key = f"user_info:{user_id}"
        result = CacheService._delete(key)
        logger.info(f"[CACHE USER] DEL user_id={user_id} result={result}")
        return result

    # ==================== 统计数据缓存（5~10分钟 + 异步刷新） ====================

    @staticmethod
    def set_stats(user_id: int, data: dict, workspace_id: int = None) -> bool:
        """缓存统计概览数据"""
        key = f"stats:overview:{user_id}:{workspace_id or 'personal'}"
        result = CacheService._set_json(key, data, settings.STATS_CACHE_TTL)
        logger.info(f"[CACHE STATS] SET user_id={user_id} ws={workspace_id or 'personal'} result={result}")
        return result

    @staticmethod
    def get_stats(user_id: int, workspace_id: int = None) -> Optional[dict]:
        """获取统计数据缓存"""
        key = f"stats:overview:{user_id}:{workspace_id or 'personal'}"
        result = CacheService._get_json(key)
        if result is not None:
            logger.info(f"[CACHE STATS] HIT user_id={user_id} ws={workspace_id or 'personal'}")
        else:
            logger.info(f"[CACHE STATS] MISS user_id={user_id} ws={workspace_id or 'personal'}")
        return result

    @staticmethod
    def delete_stats(user_id: int, workspace_id: int = None) -> bool:
        """删除统计数据缓存"""
        key = f"stats:overview:{user_id}:{workspace_id or 'personal'}"
        result = CacheService._delete(key)
        logger.info(f"[CACHE STATS] DEL user_id={user_id} ws={workspace_id or 'personal'} result={result}")
        return result

    @staticmethod
    def refresh_stats_async(user_id: int, workspace_id: int, refresh_fn: Callable) -> None:
        """异步刷新统计缓存（stale-while-revalidate）：
        先返回旧缓存，后台重新计算并写入新缓存"""
        import threading

        def _refresh():
            try:
                from app.db.session import SessionLocal
                db = SessionLocal()
                try:
                    data = refresh_fn(db, user_id, workspace_id)
                    if data:
                        CacheService.set_stats(user_id, data, workspace_id)
                        logger.info(f"[CACHE STATS] ASYNC_REFRESH_OK user_id={user_id} ws={workspace_id}")
                finally:
                    db.close()
            except Exception as e:
                logger.warning(f"[CACHE STATS] ASYNC_REFRESH_FAIL user_id={user_id} ws={workspace_id} error={e}")

        thread = threading.Thread(target=_refresh, daemon=True)
        thread.start()
        logger.info(f"[CACHE STATS] ASYNC_REFRESH_START user_id={user_id} ws={workspace_id}")

    @staticmethod
    def invalidate_user_stats(user_id: int) -> int:
        """删除用户所有统计缓存（任务变更时调用）"""
        deleted = CacheService._invalidate_pattern(f"stats:*:{user_id}:*")
        logger.info(f"[CACHE STATS] INVALIDATE_USER user_id={user_id} deleted={deleted}")
        return deleted

    # ==================== 工作空间成员权限缓存（高频权限校验） ====================

    @staticmethod
    def set_member_permission(workspace_id: int, user_id: int, role: str) -> bool:
        """缓存用户在工作空间中的角色"""
        key = f"ws_member:{workspace_id}:{user_id}"
        result = CacheService._set_json(key, {"role": role}, settings.PERMISSION_CACHE_TTL)
        logger.info(f"[CACHE PERM] SET ws={workspace_id} user={user_id} role={role} result={result}")
        return result

    @staticmethod
    def get_member_permission(workspace_id: int, user_id: int) -> Optional[dict]:
        """获取成员权限缓存"""
        key = f"ws_member:{workspace_id}:{user_id}"
        result = CacheService._get_json(key)
        if result is not None:
            logger.info(f"[CACHE PERM] HIT ws={workspace_id} user={user_id} role={result.get('role')}")
        else:
            logger.info(f"[CACHE PERM] MISS ws={workspace_id} user={user_id}")
        return result

    @staticmethod
    def delete_member_permission(workspace_id: int, user_id: int) -> bool:
        """删除单个成员权限缓存"""
        key = f"ws_member:{workspace_id}:{user_id}"
        result = CacheService._delete(key)
        logger.info(f"[CACHE PERM] DEL ws={workspace_id} user={user_id} result={result}")
        return result

    @staticmethod
    def invalidate_workspace_permissions(workspace_id: int) -> int:
        """删除工作空间所有成员权限缓存（成员变更时调用）"""
        deleted = CacheService._invalidate_pattern(f"ws_member:{workspace_id}:*")
        logger.info(f"[CACHE PERM] INVALIDATE_WS ws={workspace_id} deleted={deleted}")
        return deleted

    # ==================== 热点任务详情缓存 ====================

    @staticmethod
    def set_task_detail(task_id: int, data: dict) -> bool:
        """缓存任务详情"""
        key = f"task_detail:{task_id}"
        result = CacheService._set_json(key, data, settings.TASK_DETAIL_CACHE_TTL)
        logger.info(f"[CACHE TASK] SET task_id={task_id} result={result}")
        return result

    @staticmethod
    def get_task_detail(task_id: int) -> Optional[dict]:
        """获取任务详情缓存"""
        key = f"task_detail:{task_id}"
        result = CacheService._get_json(key)
        if result is not None:
            logger.info(f"[CACHE TASK] HIT task_id={task_id}")
        else:
            logger.info(f"[CACHE TASK] MISS task_id={task_id}")
        return result

    @staticmethod
    def delete_task_detail(task_id: int) -> bool:
        """删除任务详情缓存"""
        key = f"task_detail:{task_id}"
        result = CacheService._delete(key)
        logger.info(f"[CACHE TASK] DEL task_id={task_id} result={result}")
        return result

    # ==================== 批量失效便捷方法 ====================

    @staticmethod
    def invalidate_user_all_caches(user_id: int) -> dict:
        """一键失效用户所有缓存（登出/密码修改时调用）"""
        deleted = {
            "user_info": CacheService.delete_user_info(user_id),
            "user_categories": CacheService.delete_user_categories(user_id),
            "user_tasks": CacheService.delete_user_tasks(user_id),
            "email_change": CacheService.delete_email_change(user_id),
            "password_reset": CacheService.delete_password_reset(user_id),
            "refresh_token": CacheService.delete_refresh_token(user_id),
            "refresh_token_used": CacheService._invalidate_pattern(f"used_refresh_token:{user_id}:*"),
            "stats": CacheService.invalidate_user_stats(user_id),
            "ws_permissions": CacheService._invalidate_pattern(f"ws_member:*:{user_id}"),
        }
        return deleted


cache_service = CacheService()
