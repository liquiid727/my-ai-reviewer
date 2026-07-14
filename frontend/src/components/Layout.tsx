import { Link, Outlet, useLocation } from 'react-router'
import { Settings, ClipboardList } from 'lucide-react'
import { Button } from '@/components/ui/button'

export function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-[#e0d6ff]">
      <nav className="border-b-4 border-black bg-white px-6 py-3">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link to="/" className="text-xl font-black tracking-tight">
            AI Interview Platform
          </Link>
          <div className="flex items-center gap-2">
            <Button asChild variant={location.pathname === '/upload' ? 'default' : 'neutral'} size="sm">
              <Link to="/upload">Upload Resume</Link>
            </Button>
            <Button asChild variant={location.pathname === '/interviews' ? 'default' : 'neutral'} size="sm">
              <Link to="/interviews">
                <ClipboardList className="size-4 mr-1" />
                Interviews
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
