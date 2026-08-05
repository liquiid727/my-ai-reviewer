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
import { ResumeStyleTemplatesPage } from '@/pages/ResumeStyleTemplatesPage'
import { BuilderPage } from '@/pages/BuilderPage'
import { JDListPage } from '@/pages/JDListPage'
import { JDDetailPage } from '@/pages/JDDetailPage'
import JobTargetPage from '@/pages/JobTargetPage'
import { PlanListPage } from '@/pages/PlanListPage'
import { PlanCreatePage } from '@/pages/PlanCreatePage'
import { PlanDetailPage } from '@/pages/PlanDetailPage'

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
          <Route path="/resumes/style-templates" element={<ResumeStyleTemplatesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/resume/:id" element={<ResumePage />} />
          <Route path="/resume/:id/evaluation" element={<EvaluationPage />} />
          <Route path="/interview/:id" element={<InterviewPage />} />
          <Route path="/interview/:id/report" element={<InterviewReportPage />} />
          <Route path="/interviews" element={<InterviewListPage />} />
          <Route path="/builder/:draftId" element={<BuilderPage />} />
          <Route path="/jobs" element={<JDListPage />} />
          <Route path="/jobs/:id" element={<JDDetailPage />} />
          <Route path="/targets/:id" element={<JobTargetPage />} />
          <Route path="/plans" element={<PlanListPage />} />
          <Route path="/plans/new" element={<PlanCreatePage />} />
          <Route path="/plans/:id" element={<PlanDetailPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
