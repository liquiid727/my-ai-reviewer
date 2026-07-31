import { BrowserRouter, Routes, Route, Navigate } from 'react-router'
import { Toaster } from '@/components/ui/sonner'
import { Layout } from '@/components/Layout'
import { UploadPage } from '@/pages/UploadPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ResumePage } from '@/pages/ResumePage'
import { EvaluationPage } from '@/pages/EvaluationPage'
import { InterviewPage } from '@/pages/InterviewPage'
import { InterviewReportPage } from '@/pages/InterviewReportPage'
import { InterviewListPage } from '@/pages/InterviewListPage'
import { MyResumesPage } from '@/pages/MyResumesPage'
import { BuilderPage } from '@/pages/BuilderPage'

export default function App() {
  return (
    <BrowserRouter>
      {/* 页面级提示居中显示，使用 Neobrutalism 主题化 Toaster（黑边硬阴影，与 Alert 规范一致） */}
      <Toaster position="top-center" />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/resumes" element={<MyResumesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/resume/:id" element={<ResumePage />} />
          <Route path="/resume/:id/evaluation" element={<EvaluationPage />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
          <Route path="/interview/:id/report" element={<InterviewReportPage />} />
          <Route path="/interviews" element={<InterviewListPage />} />
          <Route path="/builder/:draftId" element={<BuilderPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
