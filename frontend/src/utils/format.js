/**
 * 将 UTC 时间字符串转换为 UTC+8 (北京时间) 显示格式
 * @param {string} utcStr - ISO 时间字符串
 * @returns {string} YYYY-MM-DD HH:MM:SS
 */
export function formatTime(utcStr) {
  if (!utcStr) return ''
  
  // 使用 Intl.DateTimeFormat 明确指定时区为北京时区
  const formatter = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  })
  
  const date = new Date(utcStr)
  const result = formatter.format(date)
  
  // 将格式化结果转换为 YYYY-MM-DD HH:MM:SS 格式
  const parts = result.split(/[/\s:]/)
  if (parts.length >= 6) {
    // 格式是 年/月/日 时:分:秒
    return `${parts[2]}-${parts[1]}-${parts[0]} ${parts[3]}:${parts[4]}:${parts[5]}`
  }
  
  return result
}

/**
 * 格式化日期时间（同formatTime，别名函数）
 */
export function formatDate(dateStr) {
  return formatTime(dateStr)
}
