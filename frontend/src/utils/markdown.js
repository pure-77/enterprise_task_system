/**
 * Markdown 渲染工具
 * 渲染 Agent 回复里的 **粗体**、*斜体*、`代码`、列表、代码块 等
 */
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight(str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return '<pre class="hljs"><code>' +
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value +
          '</code></pre>'
      } catch (_) {}
    }
    return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
  }
})

export function renderMarkdown(text) {
  if (!text) return ''
  return md.render(text)
}
