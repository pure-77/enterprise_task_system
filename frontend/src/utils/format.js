/**
 * 时间格式化工具 — 统一处理后端返回的 ISO 8601 时间字符串
 * 支持的格式：2026-08-01T13:29:47、2026-08-01T13:29:47.000Z、2026-08-01 13:29:47
 * 输出格式：YYYY-MM-DD HH:mm:ss
 */

/**
 * 将任意时间字符串或 Date 对象格式化为 YYYY-MM-DD HH:mm:ss
 * @param {string|Date} input - 时间字符串或 Date 对象
 * @param {string} fallback - 格式化失败时返回的默认值
 * @returns {string} YYYY-MM-DD HH:mm:ss
 */
export function formatTime(input, fallback = '') {
  if (!input) return fallback

  let date
  if (input instanceof Date) {
    date = input
  } else if (typeof input === 'string') {
    // 处理 ISO 8601 格式：去掉 T 和 Z 等符号
    const cleaned = input
      .replace(/T/g, ' ')      // 2026-08-01T13:29:47 → 2026-08-01 13:29:47
      .replace(/\.\d+/g, '')    // 2026-08-01T13:29:47.000 → 去掉毫秒
      .replace(/Z/g, '')        // 去掉 UTC 标识
      .replace(/[+-]\d{2}:\d{2}$/, '')  // 去掉时区偏移
    date = new Date(cleaned)
    if (isNaN(date.getTime())) {
      // 后端可能返回带时区偏移的字符串，用 replace 后仍解析失败
      // 尝试直接用原字符串构造
      date = new Date(input)
    }
  } else {
    return fallback
  }

  if (isNaN(date.getTime())) return fallback

  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

/**
 * 仅格式化日期部分 YYYY-MM-DD
 */
export function formatDateOnly(input, fallback = '') {
  if (!input) return fallback
  const result = formatTime(input, null)
  if (!result) return fallback
  return result.split(' ')[0]
}

/**
 * 相对时间（刚刚 / N分钟前 / N小时前 / N天前）
 */
export function formatRelative(input, fallback = '') {
  if (!input) return fallback
  const cleaned = input
    .replace(/T/g, ' ')
    .replace(/\.\d+/g, '')
    .replace(/Z/g, '')
    .replace(/[+-]\d{2}:\d{2}$/, '')
  const date = new Date(cleaned)
  if (isNaN(date.getTime())) return fallback

  const diff = Date.now() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (hours < 24) return `${hours}小时前`
  if (days < 30) return `${days}天前`
  return formatTime(input, fallback)
}

// 兼容旧名称
export const formatDate = formatTime

/**
 * 仅格式化时间部分 HH:mm:ss
 */
export function formatTimeOnly(input, fallback = '') {
  if (!input) return fallback
  const result = formatTime(input, null)
  if (!result) return fallback
  return result.split(' ')[1] || fallback
}

/**
 * 格式化时间为 HH:mm
 */
export function formatTimeShort(input, fallback = '') {
  if (!input) return fallback
  const result = formatTime(input, null)
  if (!result) return fallback
  const parts = result.split(' ')
  const timePart = parts[1] || ''
  return timePart.substring(0, 5) || fallback
}

/**
 * 微信风格的聊天时间格式化
 * - 今天: HH:mm
 * - 昨天: 昨天 HH:mm
 * - 本年: MM月DD日 HH:mm
 * - 非本年: YYYY年MM月DD日 HH:mm
 */
export function formatChatTime(input, fallback = '') {
  if (!input) return fallback
  const result = formatTime(input, null)
  if (!result) return fallback

  const [datePart, timePart] = result.split(' ')
  if (!datePart || !timePart) return fallback

  const [year, month, day] = datePart.split('-').map(Number)
  const [hour, minute] = timePart.split(':').map(Number)

  const now = new Date()
  const msgDate = new Date(year, month - 1, day)

  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterdayStart = new Date(todayStart)
  yesterdayStart.setDate(yesterdayStart.getDate() - 1)

  const pad = (n) => String(n).padStart(2, '0')
  const timeStr = `${pad(hour)}:${pad(minute)}`

  // 今天
  if (msgDate.getTime() === todayStart.getTime()) {
    return timeStr
  }
  // 昨天
  if (msgDate.getTime() === yesterdayStart.getTime()) {
    return `昨天 ${timeStr}`
  }
  // 本年
  if (year === now.getFullYear()) {
    return `${pad(month)}月${pad(day)}日 ${timeStr}`
  }
  // 非本年
  return `${year}年${pad(month)}月${pad(day)}日 ${timeStr}`
}
