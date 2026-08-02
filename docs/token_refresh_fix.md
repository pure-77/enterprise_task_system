# 双Token刷新认证修复记录

## 问题现象

昨天登录成功，今天刷新页面后直接回退到登录页，localStorage 中 `access_token` 和 `refresh_token` 均丢失。

## 根因

前后端共 5 个 Bug 形成链式反应：

```
access_token 过期(30min)
  → 任意 API 返回 401
    → 401 拦截器尝试刷新
      → 刷新失败(任一原因)
        → 清空所有 token → 跳转登录页
```

---

## 修复清单

### 后端

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 1 | `backend/app/api/v1/auth.py` | 多标签页场景下，重放检测会**删除当前有效 token**，导致所有标签页 session 被销毁 | 重放检测仅拒绝请求，不再删除有效 token |

### 前端

| # | 文件 | 问题 | 修复 |
|---|------|------|------|
| 2 | `frontend/src/api/request.js` | `useUserStore` 未 import，401 拦截器内 4 处调用全部 `ReferenceError` | 添加 `import { useUserStore }` |
| 3 | `frontend/src/router/index.js` | 每次路由跳转都调 `loadUserInfo()`，频繁触发 401→刷新链条 | 移除路由守卫中的 `loadUserInfo()` 调用 |
| 4 | `frontend/src/pinia/userStore.js` | `checkAuth()` 永远返回 `true`，过期 token 被当作有效 | 本地解码 JWT 检查 `exp`，过期时主动刷新 |
| 5 | `frontend/src/api/request.js` | 网络错误也清空 token，瞬断即登出 | 仅 401 响应才清空 token；网络错误保留 token 提示重试 |
| 6 | `frontend/src/views/User/Profile.vue` | localStorage key 错误 `'token'` → 应为 `'access_token'` | 修正 key |

---

## 新增工具函数

`frontend/src/utils/auth.js` 新增：

- `decodeJWTPayload(token)` — 本地解码 JWT payload（不验证签名，仅读取 exp）
- `auth.isAccessTokenExpired()` — 判断 access_token 是否过期
- `auth.isRefreshTokenExpired()` — 判断 refresh_token 是否过期

---

## 修复后的流程

```
页面加载
  → initAuth()
    → checkAuth()
      → 本地解码 JWT，检查 exp
      → 未过期 → 直接通过
      → 已过期 → 有 refresh_token → 主动刷新
        → 成功 → 更新 token，继续
        → 失败 → 清空状态，跳转登录
  → 路由守卫：仅检查 isLoggedIn，不再触发 API 调用
  → API 调用 401
    → 拦截器刷新
      → 成功 → 重试请求
      → 401 → 清空 token，跳转登录（refresh_token 真的无效）
      → 网络错误 → 保留 token，提示"刷新重试"
```
