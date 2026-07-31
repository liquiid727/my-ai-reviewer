import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { Trash2, Pencil, Plus, Loader2, BadgeCheck, BadgeAlert } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

import { deleteLLMConfig } from '@/api/settings'
import { LLMConfigForm } from '@/components/LLMConfigForm'
import { PROVIDER_LABELS } from '@/lib/llm-providers'
import { useSettingsStore } from '@/stores/settingsStore'
import type { LLMConfig } from '@/types/settings'

export function SettingsPage() {
  const { t } = useTranslation()
  const { configs, loading, loaded, refresh } = useSettingsStore()
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  // 待确认删除的配置 ID：用统一 Dialog 替代原生 window.confirm
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  useEffect(() => {
    refresh()
  }, [refresh])

  function handleEdit(config: LLMConfig) {
    // 再次点击同一项的编辑按钮 = 退出编辑（开关式交互）
    if (editingConfig?.id === config.id) {
      setEditingConfig(null)
      return
    }
    setEditingConfig(config)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function handleDelete(id: string) {
    setDeletingId(id)
    try {
      const res = await deleteLLMConfig(id)
      if (res.code === 0) {
        toast.success(t('settings.deleted'))
        if (editingConfig?.id === id) {
          setEditingConfig(null)
        }
        await refresh()
      } else {
        toast.error(t('settings.deleteError', { msg: res.message }))
      }
    } catch {
      toast.error(t('settings.deleteErrorGeneric'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div>
        <h1 className="text-3xl font-black">{t('settings.title')}</h1>
        <p className="mt-1 text-muted-foreground">{t('settings.subtitle')}</p>
      </div>

      {/* 两栏布局：大屏左侧表单 + 右侧常驻配置列表，小屏自动堆叠 */}
      <div className="grid gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] lg:items-start">
        {/* Config Form */}
        <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl font-black">
            {editingConfig ? (
              <>
                <Pencil className="size-5" />
                {t('settings.editTitle')}
              </>
            ) : (
              <>
                <Plus className="size-5" />
                {t('settings.addTitle')}
              </>
            )}
          </CardTitle>
          <CardDescription>
            {editingConfig ? t('settings.editDesc') : t('settings.addDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <LLMConfigForm
            editingConfig={editingConfig}
            onSaved={(_config, verified) => {
              // 退出编辑会重置表单内联反馈，改用 toast 告知结果（与删除流程一致）
              if (editingConfig) {
                if (verified) {
                  toast.success(t('settings.updated'))
                } else {
                  toast.warning(t('settings.updatedButUnverified'))
                }
                setEditingConfig(null)
              }
            }}
            onCancelEdit={() => setEditingConfig(null)}
          />
        </CardContent>
        </Card>

        {/* Saved Configs List：大屏下同页常驻（sticky），无需滚动即可查看 */}
        <Card className="lg:sticky lg:top-8">
        <CardHeader>
          <CardTitle className="text-xl font-black">
            {t('settings.savedConfigs')}
          </CardTitle>
          <CardDescription>
            {configs.length === 0 && loaded
              ? t('settings.noConfigs')
              : t('settings.configsCount', { count: configs.length })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading && !loaded ? (
            <div className="flex items-center justify-center py-8 text-foreground/50">
              <Loader2 className="mr-2 size-5 animate-spin" />
              {t('common.loading')}
            </div>
          ) : configs.length === 0 ? (
            <div className="py-8 text-center text-foreground/50">
              {t('settings.noConfigs')}
            </div>
          ) : (
            <div className="space-y-3">
              {configs.map((config) => (
                <div
                  key={config.id}
                  className={`flex flex-col gap-3 rounded-base border-2 border-border p-4 sm:flex-row sm:items-center sm:justify-between lg:flex-col lg:items-stretch ${
                    editingConfig?.id === config.id
                      ? 'bg-main/30 shadow-shadow'
                      : 'bg-secondary-background'
                  }`}
                >
                  <div className="flex flex-col gap-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold">
                        {PROVIDER_LABELS[config.provider] ?? config.provider}
                      </span>
                      <Badge variant="neutral">{config.model_name}</Badge>
                      {editingConfig?.id === config.id && (
                        <Badge>
                          <Pencil className="size-3.5" />
                          {t('settings.editing')}
                        </Badge>
                      )}
                      {config.is_active && <Badge>{t('common.active')}</Badge>}
                      {config.verified ? (
                        <Badge className="bg-green-500 text-white">
                          <BadgeCheck className="size-3.5" />
                          {t('settings.verified')}
                        </Badge>
                      ) : (
                        <Badge className="bg-yellow-400 text-black">
                          <BadgeAlert className="size-3.5" />
                          {t('settings.unverified')}
                        </Badge>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-foreground/60">
                      <span className="font-mono">{config.api_key}</span>
                      {config.base_url && (
                        <span className="truncate max-w-[200px]">
                          {config.base_url}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      size="sm"
                      variant={
                        editingConfig?.id === config.id ? 'default' : 'neutral'
                      }
                      aria-pressed={editingConfig?.id === config.id}
                      onClick={() => handleEdit(config)}
                    >
                      <Pencil className="size-3.5" />
                      {editingConfig?.id === config.id
                        ? t('common.cancel')
                        : t('common.edit')}
                    </Button>
                    <Button
                      size="sm"
                      variant="neutral"
                      disabled={deletingId === config.id}
                      onClick={() => setConfirmDeleteId(config.id)}
                    >
                      {deletingId === config.id ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="size-3.5" />
                      )}
                      {t('common.delete')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
        </Card>
      </div>

      {/* 删除确认弹窗：统一 Dialog 组件替代原生 window.confirm */}
      <Dialog
        open={confirmDeleteId !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmDeleteId(null)
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('common.delete')}</DialogTitle>
            <DialogDescription>
              {t('settings.deleteConfirm')}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="neutral"
              onClick={() => setConfirmDeleteId(null)}
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={() => {
                if (confirmDeleteId) handleDelete(confirmDeleteId)
                setConfirmDeleteId(null)
              }}
            >
              <Trash2 className="size-3.5" />
              {t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
