import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { changeLanguage, type AppLanguage } from '@/i18n/config'

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const current: AppLanguage = i18n.language === 'zh' ? 'zh' : 'en'
  const next: AppLanguage = current === 'zh' ? 'en' : 'zh'

  return (
    <Button
      variant="neutral"
      size="icon"
      onClick={() => changeLanguage(next)}
      aria-label={current === 'zh' ? 'Switch to English' : '切换为中文'}
      title={current === 'zh' ? 'Switch to English' : '切换为中文'}
      className="text-xs font-bold"
    >
      {current === 'zh' ? '中' : 'EN'}
    </Button>
  )
}
