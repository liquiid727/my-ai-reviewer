import { useTranslation } from 'react-i18next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { changeLanguage, type AppLanguage } from '@/i18n/config'

export function LanguageSwitcher() {
  const { i18n } = useTranslation()
  const current: AppLanguage = i18n.language === 'zh' ? 'zh' : 'en'

  return (
    <Select
      value={current}
      onValueChange={(value) => changeLanguage(value as AppLanguage)}
    >
      <SelectTrigger className="h-9 w-[104px]" aria-label="Language">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="en">EN</SelectItem>
        <SelectItem value="zh">中文</SelectItem>
      </SelectContent>
    </Select>
  )
}
