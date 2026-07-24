import i18n from './config'

/** Format an ISO date string using the currently selected UI language. */
export function formatDateTime(value?: string): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const locale = i18n.language === 'zh' ? 'zh-CN' : 'en-US'
  return d.toLocaleString(locale, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
