import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { formatDateTime } from '@/i18n'
import { getResumeStatus } from '@/api/resume'
import { createDraftFromResume, createDraftFromReference, listDrafts, listReferenceTemplates } from '@/api/builder'
import type { DraftListItem, ReferenceTemplateItem } from '@/types/builder'
import { useResumeHistoryStore, MAX_HISTORY, type ResumeHistoryEntry } from '@/stores/resumeHistoryStore'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  ArrowRight,
  Calendar,
  CircleAlert,
  Eye,
  FileEdit,
  FileText,
  LayoutTemplate,
  Loader2,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'

// 简历处理状态 → 徽标配色（Neobrutalism 高对比配色，与面试列表一致）
const STATUS_COLORS: Record<string, string> = {
  uploaded: 'bg-gray-300 text-gray-800 border-gray-500',
  text_parsed: 'bg-blue-300 text-blue-900 border-blue-600',
  fact_extracted: 'bg-blue-300 text-blue-900 border-blue-600',
  classified: 'bg-yellow-300 text-yellow-900 border-yellow-600',
  evaluated: 'bg-green-400 text-green-900 border-green-700',
  failed: 'bg-red-400 text-red-900 border-red-700',
}

function UploadedResumeCard({
  entry,
  onDelete,
}: {
  entry: ResumeHistoryEntry
  onDelete: (id: string) => void
}) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [buildingDraft, setBuildingDraft] = useState(false)

  const statusColor = STATUS_COLORS[entry.status] || 'bg-gray-300'
  const canBuild = entry.status === 'evaluated' || entry.status === 'classified'

  // 编辑润色 = 基于该简历创建可编辑草稿并进入 Builder（编辑 / AI 润色 / 打分 / 导出）
  const handleEditPolish = async () => {
    setBuildingDraft(true)
    try {
      const res = await createDraftFromResume(entry.resume_id)
      if (res.code !== 0) {
        toast.error(res.message || t('builder.createFailed'))
        return
      }
      navigate(`/builder/${res.data.draft_id}`)
    } catch (err) {
      toast.error((err as Error).message || t('builder.createFailed'))
    } finally {
      setBuildingDraft(false)
    }
  }

  return (
    <Card className="hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
      <CardHeader>
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="text-base flex items-center gap-2 min-w-0">
            <FileText className="size-4 shrink-0" />
            <span className="truncate">{entry.file_name}</span>
            <Badge className={statusColor}>
              {t(`myResumes.status.${entry.status}`, { defaultValue: entry.status })}
            </Badge>
          </CardTitle>
          <button
            type="button"
            onClick={() => onDelete(entry.resume_id)}
            className="p-1 hover:bg-red-100 rounded-base shrink-0"
            aria-label={t('common.delete')}
          >
            <Trash2 className="size-4 text-red-600" />
          </button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-between gap-2">
          <span className="flex items-center gap-1 text-sm text-muted-foreground">
            <Calendar className="size-3" />
            {formatDateTime(entry.uploaded_at)}
          </span>
          <div className="flex gap-2">
            <Button asChild size="sm" variant="neutral">
              <Link to={`/resume/${entry.resume_id}`}>
                <Eye className="size-4" />
                {t('myResumes.view')}
              </Link>
            </Button>
            <Button size="sm" onClick={handleEditPolish} disabled={!canBuild || buildingDraft}>
              {buildingDraft ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <FileEdit className="size-4" />
              )}
              {t('myResumes.editPolish')}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function MyResumesPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { entries, updateStatus, removeEntry } = useResumeHistoryStore()
  const [drafts, setDrafts] = useState<DraftListItem[]>([])
  const [draftsLoading, setDraftsLoading] = useState(true)
  const [draftsError, setDraftsError] = useState<string | null>(null)
  const [templates, setTemplates] = useState<ReferenceTemplateItem[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(true)
  const [creatingKey, setCreatingKey] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<ResumeHistoryEntry | null>(null)

  // 进入页面时逐条拉后端最新状态刷新本地缓存；单条失败回退本地缓存，不阻塞整页
  useEffect(() => {
    const ids = useResumeHistoryStore.getState().entries.map((e) => e.resume_id)
    ids.forEach((id) => {
      getResumeStatus(id)
        .then((res) => {
          if (res.code === 0 && res.data?.status) {
            updateStatus(id, res.data.status)
          }
        })
        .catch(() => {
          // 请求失败时保留本地缓存状态
        })
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 后端草稿列表（编辑中的简历，含从参考模板创建的草稿）
  useEffect(() => {
    setDraftsLoading(true)
    listDrafts()
      .then((res) => {
        if (res.code !== 0) {
          setDraftsError(res.message || t('myResumes.draftsLoadFailed'))
          return
        }
        setDrafts(res.data || [])
      })
      .catch((err: Error) => setDraftsError(err.message || t('myResumes.draftsLoadFailed')))
      .finally(() => setDraftsLoading(false))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 内置参考模板列表
  useEffect(() => {
    listReferenceTemplates()
      .then((res) => {
        if (res.code === 0) setTemplates(res.data || [])
      })
      .catch(() => {
        // 模板加载失败不阻塞页面，Tab 内展示空态
      })
      .finally(() => setTemplatesLoading(false))
  }, [])

  const handleUseTemplate = useCallback(async (key: string) => {
    setCreatingKey(key)
    try {
      const res = await createDraftFromReference(key)
      if (res.code !== 0) {
        toast.error(res.message || t('builder.createFailed'))
        return
      }
      toast.success(t('myResumes.templateCreated'))
      navigate(`/builder/${res.data.draft_id}`)
    } catch (err) {
      toast.error((err as Error).message || t('builder.createFailed'))
    } finally {
      setCreatingKey(null)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [navigate])

  const confirmDelete = () => {
    if (deleteTarget) {
      removeEntry(deleteTarget.resume_id)
      toast.success(t('myResumes.deleted'))
      setDeleteTarget(null)
    }
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-black">{t('myResumes.title')}</h1>
        <Button asChild>
          <Link to="/upload">
            <Upload className="size-4" />
            {t('myResumes.uploadNew')}
          </Link>
        </Button>
      </div>

      <Tabs defaultValue="uploads">
        <TabsList className="flex flex-wrap h-auto gap-1">
          <TabsTrigger value="uploads" className="gap-1">
            <FileText className="size-4" />
            {t('myResumes.tabs.uploads')}
          </TabsTrigger>
          <TabsTrigger value="drafts" className="gap-1">
            <FileEdit className="size-4" />
            {t('myResumes.tabs.drafts')}
          </TabsTrigger>
          <TabsTrigger value="templates" className="gap-1">
            <LayoutTemplate className="size-4" />
            {t('myResumes.tabs.templates')}
          </TabsTrigger>
        </TabsList>

        {/* ───────── 我的上传（localStorage 历史，最多 10 条） ───────── */}
        <TabsContent value="uploads">
          <div className="space-y-4">
            {entries.length > 0 && (
              <p className="text-sm text-muted-foreground">
                {t('myResumes.limitHint', { count: entries.length, max: MAX_HISTORY })}
              </p>
            )}
            {entries.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-4 py-12">
                  <p className="text-lg text-muted-foreground">{t('myResumes.noUploads')}</p>
                  <Button asChild>
                    <Link to="/upload">
                      <Upload className="size-4" />
                      {t('myResumes.uploadToStart')}
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {entries.map((entry) => (
                  <UploadedResumeCard
                    key={entry.resume_id}
                    entry={entry}
                    onDelete={() => setDeleteTarget(entry)}
                  />
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* ───────── 简历草稿（后端持久化，可继续编辑/润色/导出） ───────── */}
        <TabsContent value="drafts">
          <div className="space-y-4">
            {draftsLoading ? (
              <div className="grid gap-4">
                {[1, 2].map((i) => (
                  <Skeleton key={i} className="h-24 w-full" />
                ))}
              </div>
            ) : draftsError ? (
              <Alert variant="destructive">
                <CircleAlert />
                <AlertDescription>{draftsError}</AlertDescription>
              </Alert>
            ) : drafts.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-4 py-12">
                  <p className="text-lg text-muted-foreground">{t('myResumes.noDrafts')}</p>
                  <p className="text-sm text-muted-foreground">{t('myResumes.noDraftsHint')}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {drafts.map((d) => (
                  <Card
                    key={d.draft_id}
                    className="hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
                  >
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileEdit className="size-4 shrink-0" />
                        <span className="truncate">{d.title}</span>
                        <Badge variant="neutral">
                          {t(`builder.template_${d.template_id}`, { defaultValue: d.template_id })}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center justify-between gap-2">
                        <span className="flex items-center gap-1 text-sm text-muted-foreground">
                          <Calendar className="size-3" />
                          {t('myResumes.updatedAt', { time: formatDateTime(d.updated_at) })}
                        </span>
                        <Button asChild size="sm">
                          <Link to={`/builder/${d.draft_id}`}>
                            {t('myResumes.continueEditing')}
                            <ArrowRight className="size-4" />
                          </Link>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>

        {/* ───────── 参考模板（内置范本，一键创建草稿后进入编辑/润色） ───────── */}
        <TabsContent value="templates">
          <div className="space-y-4">
            {templatesLoading ? (
              <Skeleton className="h-40 w-full" />
            ) : templates.length === 0 ? (
              <Card>
                <CardContent className="flex flex-col items-center gap-4 py-12">
                  <p className="text-lg text-muted-foreground">{t('myResumes.noTemplates')}</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2">
                {templates.map((tpl) => (
                  <Card key={tpl.key}>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Sparkles className="size-4 shrink-0" />
                        {tpl.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <p className="text-sm text-muted-foreground">{tpl.description}</p>
                      <div className="flex flex-wrap gap-1">
                        {tpl.tags.map((tag) => (
                          <Badge key={tag} variant="neutral" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <Button
                        size="sm"
                        onClick={() => handleUseTemplate(tpl.key)}
                        disabled={creatingKey !== null}
                      >
                        {creatingKey === tpl.key ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <FileEdit className="size-4" />
                        )}
                        {t('myResumes.useTemplate')}
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* 删除本地记录二次确认（仅删 localStorage，不调用后端） */}
      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('myResumes.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('myResumes.deleteDesc', { name: deleteTarget?.file_name ?? '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="neutral" onClick={() => setDeleteTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button className="bg-red-500 text-white" onClick={confirmDelete}>
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
