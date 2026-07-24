import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import { en } from './locales/en'
import { zh } from './locales/zh'

export const SUPPORTED_LANGUAGES = ['en', 'zh'] as const
export type AppLanguage = (typeof SUPPORTED_LANGUAGES)[number]

const STORAGE_KEY = 'app-lang'

function getInitialLanguage(): AppLanguage {
  if (typeof localStorage !== 'undefined') {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'en' || saved === 'zh') return saved
  }
  return 'en'
}

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    zh: { translation: zh },
  },
  lng: getInitialLanguage(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export function changeLanguage(lang: AppLanguage) {
  i18n.changeLanguage(lang)
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(STORAGE_KEY, lang)
  }
}

export default i18n
