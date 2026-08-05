import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { formatDateTime } from '@/i18n'
import { getResumeStatus } from '@/api/resume'
import {
  createDraftFromResume,
  createDraftFromReference,
  deleteDraft,
  listDrafts,
  listReferenceTemplates,
  previewUrl,
  reorderDrafts,
} from '@/api/builder'
import type { DraftListItem, ReferenceTemplateItem } from '@/types/builder'
import { useResumeHistoryStore, MAX_HISTORY, type ResumeHistoryEntry } from '@/stores/resumeHistoryStore'
import { StartInterviewDialog } from '@/components/interview/StartInterviewDialog'
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
  ArrowDown,
  ArrowUp,
  Calendar,
  CircleAlert,
  ClipboardPlus,
  Eye,
  FileEdit,
  FileText,
  LayoutTemplate,
  Loader2,
  MessageSquare,
  Palette,
  Sparkles,
  Trash2,
  Upload,
} from 'lucide-react'

// 简历处理状态 → 徽标配色（Neobrutalism 高对比配色，与面试列表一致）
const STATUS_COLORS: Record<string, string> = {
  uploaded: 'bg-gray-300 text-gray-800 border-gray-500',
  privacy_review_required: 'bg-orange-300 text-orange-900 border-orange-600',
  text_masked: 'bg-blue-300 text-blue-900 border-blue-600',
  llm_parsing: 'bg-blue-300 text-blue-900 border-blue-600',
  text_parsed: 'bg-blue-300 text-blue-900 border-blue-600',
  fact_extracted: 'bg-blue-300 text-blue-900 border-blue-600',
  classified: 'bg-yellow-300 text-yellow-900 border-yellow-600',
  evaluating: 'bg-yellow-300 text-yellow-900 border-yellow-600',
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
  const [interviewOpen, setInterviewOpen] = useState(false)

  const statusColor = STATUS_COLORS[entry.status] || 'bg-gray-300'
  const canBuild = entry.status === 'evaluated' || entry.status === 'classified'
  // 解析/上传失败的简历：除删除外禁用所有查看与操作入口
  const isFailed = entry.status === 'failed'

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
            <Button
              size="sm"
              variant="neutral"
              disabled={isFailed}
              title={isFailed ? t('myResumes.failedHint') : undefined}
              onClick={() => navigate(`/resume/${entry.resume_id}`)}
            >
              <Eye className="size-4" />
              {t('myResumes.view')}
            </Button>
            <Button
              size="sm"
              onClick={handleEditPolish}
              disabled={!canBuild || buildingDraft}
              title={!canBuild ? (isFailed ? t('myResumes.failedHint') : t('myResumes.notReadyHint')) : undefined}
            >
              {buildingDraft ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <FileEdit className="size-4" />
              )}
              {t('myResumes.editPolish')}
            </Button>
            {canBuild && (
              <Button asChild size="sm" variant="neutral">
                <Link to={`/plans/new?resume_id=${entry.resume_id}`}>
                  <ClipboardPlus className="size-4" />
                  {t('plans.create')}
                </Link>
              </Button>
            )}
            {canBuild && (
              <Button size="sm" onClick={() => setInterviewOpen(true)}>
                <MessageSquare className="size-4" />
                {t('myResumes.startInterview')}
              </Button>
            )}
          </div>
        </div>
        {isFailed && (
          <p className="mt-2 text-xs text-red-700">{t('myResumes.failedHint')}</p>
        )}
      </CardContent>
      <StartInterviewDialog
        open={interviewOpen}
        onOpenChange={setInterviewOpen}
        resumeId={entry.resume_id}
      />
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
  const [draftDeleteTarget, setDraftDeleteTarget] = useState<DraftListItem | null>(null)
  const [previewTarget, setPreviewTarget] = useState<DraftListItem | null>(null)
  const [previewState, setPreviewState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [deletingDraftId, setDeletingDraftId] = useState<string | null>(null)
  const [movingDraftId, setMovingDraftId] = useState<string | null>(null)
  // 草稿卡片发起面试：记录选中草稿 id，以草稿当前内容作为出题依据（null 表示对话框关闭）
  const [draftInterviewDraftId, setDraftInterviewDraftId] = useState<string | null>(null)

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

  const handleDeleteDraft = async () => {
    if (!draftDeleteTarget) return
    const target = draftDeleteTarget
    setDeletingDraftId(target.draft_id)
    try {
      const res = await deleteDraft(target.draft_id)
      if (res.code !== 0) {
        throw new Error(res.message || t('myResumes.draftDeleteFailed'))
      }
      setDrafts((current) => current.filter((draft) => draft.draft_id !== target.draft_id))
      setDraftDeleteTarget(null)
      toast.success(t('myResumes.draftDeleted'))
    } catch (err) {
      toast.error((err as Error).message || t('myResumes.draftDeleteFailed'))
    } finally {
      setDeletingDraftId(null)
    }
  }

  const handleMoveDraft = async (draftId: string, direction: -1 | 1) => {
    if (movingDraftId) return
    const currentIndex = drafts.findIndex((draft) => draft.draft_id === draftId)
    const targetIndex = currentIndex + direction
    if (currentIndex < 0 || targetIndex < 0 || targetIndex >= drafts.length) return

    const previous = drafts
    const next = [...drafts]
    const [moving] = next.splice(currentIndex, 1)
    next.splice(targetIndex, 0, moving)
    setDrafts(next)
    setMovingDraftId(draftId)

    try {
      const res = await reorderDrafts(next.map((draft) => draft.draft_id))
      if (res.code !== 0) {
        throw new Error(res.message || t('myResumes.reorderFailed'))
      }
      setDrafts(res.data || next)
    } catch (err) {
      setDrafts(previous)
      toast.error((err as Error).message || t('myResumes.reorderFailed'))
    } finally {
      setMovingDraftId(null)
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
          <TabsTrigger value="styleTemplates" asChild className="gap-1">
            <Link to="/resumes/style-templates">
              <Palette className="size-4" />
              {t('myResumes.tabs.styleTemplates')}
            </Link>
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
                {drafts.map((d, index) => (
                  <Card
                    key={d.draft_id}
                    className="hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all"
                  >
                    <CardHeader className="gap-3">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <CardTitle className="flex min-w-0 flex-1 items-center gap-2 text-base">
                          <FileEdit className="size-4 shrink-0" />
                          <span className="truncate">{d.title}</span>
                          <Badge variant="neutral" className="shrink-0">
                            {t(`builder.template_${d.template_id}`, { defaultValue: d.template_id })}
                          </Badge>
                          {d.overall_score != null && (
                            <Badge className="shrink-0 bg-green-400 text-green-900 border-green-700">
                              <Sparkles className="size-3" />
                              {t('myResumes.scoreBadge', { score: d.overall_score })}
                            </Badge>
                          )}
                        </CardTitle>
                        <div className="flex shrink-0 items-center gap-1">
                          <Button
                            type="button"
                            size="icon"
                            variant="neutral"
                            title={t('myResumes.moveUp')}
                            aria-label={t('myResumes.moveUp')}
                            disabled={movingDraftId !== null || index === 0}
                            onClick={() => handleMoveDraft(d.draft_id, -1)}
                          >
                            {movingDraftId === d.draft_id ? <Loader2 className="animate-spin" /> : <ArrowUp />}
                          </Button>
                          <Button
                            type="button"
                            size="icon"
                            variant="neutral"
                            title={t('myResumes.moveDown')}
                            aria-label={t('myResumes.moveDown')}
                            disabled={movingDraftId !== null || index === drafts.length - 1}
                            onClick={() => handleMoveDraft(d.draft_id, 1)}
                          >
                            {movingDraftId === d.draft_id ? <Loader2 className="animate-spin" /> : <ArrowDown />}
                          </Button>
                          <Button
                            type="button"
                            size="icon"
                            variant="neutral"
                            className="text-red-700"
                            title={t('myResumes.deleteDraft')}
                            aria-label={t('myResumes.deleteDraft')}
                            disabled={deletingDraftId !== null || movingDraftId !== null}
                            onClick={() => setDraftDeleteTarget(d)}
                          >
                            <Trash2 />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
                        <span className="flex min-w-0 items-center gap-1 text-sm text-muted-foreground">
                          <Calendar className="size-3" />
                          <span className="truncate">{t('myResumes.updatedAt', { time: formatDateTime(d.updated_at) })}</span>
                        </span>
                        <div className="flex w-full flex-wrap gap-2 sm:w-auto sm:justify-end">
                          {/* 以草稿当前内容发起面试；独立草稿与关联简历的草稿均支持 */}
                          <Button
                            type="button"
                            size="sm"
                            onClick={() => setDraftInterviewDraftId(d.draft_id)}
                          >
                            <MessageSquare className="size-4" />
                            {t('myResumes.startInterview')}
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="neutral"
                            onClick={() => {
                              setPreviewState('loading')
                              setPreviewTarget(d)
                            }}
                          >
                            <Eye className="size-4" />
                            {t('myResumes.viewDraft')}
                          </Button>
                          <Button asChild size="sm">
                            <Link to={`/builder/${d.draft_id}`}>
                              <FileEdit className="size-4" />
                              {t('myResumes.editDraft')}
                              <ArrowRight className="size-4" />
                            </Link>
                          </Button>
                        </div>
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

      <Dialog
        open={previewTarget !== null}
        onOpenChange={(open) => {
          if (!open) setPreviewTarget(null)
        }}
      >
        <DialogContent className="h-[85vh] max-w-5xl grid-rows-[auto_minmax(0,1fr)_auto]">
          <DialogHeader>
            <DialogTitle>{t('myResumes.previewTitle', { name: previewTarget?.title ?? '' })}</DialogTitle>
            <DialogDescription>{t('myResumes.updatedAt', { time: previewTarget ? formatDateTime(previewTarget.updated_at) : '' })}</DialogDescription>
          </DialogHeader>
          <div className="relative min-h-0 overflow-hidden rounded-base border-2 border-border bg-zinc-200 shadow-shadow">
            {previewState === 'loading' && (
              <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-zinc-200 text-sm">
                <Loader2 className="size-4 animate-spin" />
                {t('common.loading')}
              </div>
            )}
            {previewState === 'error' && (
              <div className="absolute inset-0 z-10 flex items-center justify-center p-6 text-center text-sm text-red-700">
                {t('myResumes.previewFailed')}
              </div>
            )}
            {previewTarget && (
              <iframe
                key={previewTarget.draft_id}
                title={t('myResumes.previewTitle', { name: previewTarget.title })}
                src={previewUrl(previewTarget.draft_id)}
                className="h-full w-full bg-white"
                onLoad={() => setPreviewState('ready')}
                onError={() => setPreviewState('error')}
              />
            )}
          </div>
          <DialogFooter>
            <Button asChild>
              <Link to={previewTarget ? `/builder/${previewTarget.draft_id}` : '/resumes'} onClick={() => setPreviewTarget(null)}>
                <FileEdit className="size-4" />
                {t('myResumes.editDraft')}
              </Link>
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <StartInterviewDialog
        open={draftInterviewDraftId !== null}
        onOpenChange={(open) => !open && setDraftInterviewDraftId(null)}
        draftId={draftInterviewDraftId ?? undefined}
      />

      <Dialog open={draftDeleteTarget !== null} onOpenChange={(open) => !open && deletingDraftId === null && setDraftDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('myResumes.deleteDraftTitle')}</DialogTitle>
            <DialogDescription>
              {t('myResumes.deleteDraftDesc', { name: draftDeleteTarget?.title ?? '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="neutral" disabled={deletingDraftId !== null} onClick={() => setDraftDeleteTarget(null)}>
              {t('common.cancel')}
            </Button>
            <Button className="bg-red-500 text-white" disabled={deletingDraftId !== null} onClick={handleDeleteDraft}>
              {deletingDraftId ? <Loader2 className="size-4 animate-spin" /> : <Trash2 className="size-4" />}
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

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
