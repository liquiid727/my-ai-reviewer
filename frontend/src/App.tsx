import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { Toaster } from 'sonner'
import { Layout } from '@/components/Layout'
import { UploadPage } from '@/pages/UploadPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ResumePage } from '@/pages/ResumePage'
import { EvaluationPage } from '@/pages/EvaluationPage'
import { InterviewPage } from '@/pages/InterviewPage'
import { InterviewReportPage } from '@/pages/InterviewReportPage'
import { InterviewListPage } from '@/pages/InterviewListPage'

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
          <Route path="/resume/:id/evaluation" element={<EvaluationPage />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
          <Route path="/interview/:id/report" element={<InterviewReportPage />} />
          <Route path="/interviews" element={<InterviewListPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
