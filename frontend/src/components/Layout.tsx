import { Link, Outlet, useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Settings, ClipboardList } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LanguageSwitcher } from '@/components/LanguageSwitcher'

export function Layout() {
  const location = useLocation()
  const { t } = useTranslation()

  return (
    <div className="min-h-screen bg-[#e0d6ff]">
      <nav className="border-b-4 border-black bg-white px-6 py-3">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/" className="text-xl font-black tracking-tight">
            {t('app.title')}
          </Link>
          <div className="flex items-center gap-2">
            <LanguageSwitcher />
            <Button asChild variant={location.pathname === '/upload' ? 'default' : 'neutral'} size="sm">
              <Link to="/upload">{t('nav.upload')}</Link>
            </Button>
            <Button asChild variant={location.pathname === '/interviews' ? 'default' : 'neutral'} size="sm">
              <Link to="/interviews">
                <ClipboardList className="size-4 mr-1" />
                {t('nav.interviews')}
              </Link>
            </Button>
            <Button asChild variant="neutral" size="icon">
              <Link to="/settings">
                <Settings className="h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-5xl p-6">
        <Outlet />
      </main>
    </div>
  )
}
