import { useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Settings, ClipboardList, FileText, Menu, X, BriefcaseBusiness, ListChecks } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { LanguageSwitcher } from '@/components/LanguageSwitcher'

export function Layout() {
  const location = useLocation()
  const { t } = useTranslation()
  // 简历工作台需要尽可能大的内容区域：全宽 + 默认收起全局导航
  const fullBleed = location.pathname.startsWith('/builder/')
  const resumesRoute = location.pathname === '/resumes' || location.pathname.startsWith('/resumes/')
  const jobsRoute = location.pathname === '/jobs' || location.pathname.startsWith('/jobs/')
  const plansRoute = location.pathname === '/plans' || location.pathname.startsWith('/plans/')
  const [navOpen, setNavOpen] = useState(false)
  const showNav = !fullBleed || navOpen

  return (
    <div className={`bg-[#e0d6ff] ${fullBleed ? 'flex h-screen flex-col' : 'min-h-screen'}`}>
      {showNav && (
        <nav className="shrink-0 border-b-4 border-black bg-white px-6 py-3">
          <div
            className={`mx-auto flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between ${
              fullBleed ? 'pr-14' : 'max-w-5xl'
            }`}
          >
            <Link to="/" className="text-xl font-black tracking-tight">
              {t('app.title')}
            </Link>
            <div className="flex flex-wrap items-center gap-2">
              <Button asChild variant={location.pathname === '/upload' ? 'default' : 'neutral'} size="sm">
                <Link to="/upload">{t('nav.upload')}</Link>
              </Button>
              <Button asChild variant={resumesRoute ? 'default' : 'neutral'} size="sm">
                <Link to="/resumes">
                  <FileText className="size-4 mr-1" />
                  {t('nav.resumes')}
                </Link>
              </Button>
              <Button asChild variant={location.pathname === '/interviews' ? 'default' : 'neutral'} size="sm">
                <Link to="/interviews">
                  <ClipboardList className="size-4 mr-1" />
                  {t('nav.interviews')}
                </Link>
              </Button>
              <Button asChild variant={jobsRoute ? 'default' : 'neutral'} size="sm">
                <Link to="/jobs">
                  <BriefcaseBusiness className="size-4 mr-1" />
                  {t('nav.jobs')}
                </Link>
              </Button>
              <Button asChild variant={plansRoute ? 'default' : 'neutral'} size="sm">
                <Link to="/plans">
                  <ListChecks className="size-4 mr-1" />
                  {t('nav.plans')}
                </Link>
              </Button>
              <Button asChild variant="neutral" size="icon">
                <Link to="/settings">
                  <Settings className="h-4 w-4" />
                </Link>
              </Button>
              <LanguageSwitcher />
            </div>
          </div>
        </nav>
      )}
      {/* 工作台模式：导航折叠为固定右上角的切换按钮 */}
      {fullBleed && (
        <Button
          variant="neutral"
          size="icon"
          className="fixed top-4 right-3 z-50"
          title={navOpen ? t('common.hideNav') : t('common.showNav')}
          onClick={() => setNavOpen((v) => !v)}
        >
          {navOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
        </Button>
      )}
      <main className={fullBleed ? 'min-h-0 flex-1 p-3' : 'mx-auto w-full max-w-5xl p-4 sm:p-6'}>
        <Outlet />
      </main>
    </div>
  )
}
