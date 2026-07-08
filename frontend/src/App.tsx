import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { Toaster } from 'sonner'
import { Layout } from '@/components/Layout'
import { UploadPage } from '@/pages/UploadPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ResumePage } from '@/pages/ResumePage'

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/resume/:id" element={<ResumePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
