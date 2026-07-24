import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { Eye, EyeOff, Trash2, Pencil, Plus, FlaskConical, Save, Loader2, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

import {
  listLLMConfigs,
  createLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  testLLMConnection,
} from '@/api/settings'
import type { LLMConfig } from '@/types/settings'

const PROVIDERS = [
  'openai',
  'anthropic',
  'deepseek',
  'glm',
  'kimi',
  'qwen',
  'custom',
] as const

// 品牌名不翻译
const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  deepseek: 'DeepSeek',
  glm: 'GLM',
  kimi: 'Kimi',
  qwen: 'Qwen',
  custom: 'Custom',
}

// 2026 主流 + 最新模型清单（数据驱动，随厂商文档微调即可）
const PROVIDER_MODELS: Record<string, string[]> = {
  openai: [
    'gpt-5.5',
    'gpt-5.5-pro',
    'gpt-5.4',
    'gpt-5.4-pro',
    'gpt-5.4-mini',
    'gpt-5.4-nano',
    'gpt-5.2',
    'gpt-5.1',
    'gpt-5',
    'gpt-5-mini',
    'o3',
    'o3-pro',
    'gpt-4.1',
    'gpt-4.1-mini',
  ],
  anthropic: ['claude-opus-4-5', 'claude-sonnet-4-5', 'claude-haiku-4-5'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  glm: ['glm-5.2', 'glm-5.1', 'glm-5', 'glm-4.7', 'glm-4.6'],
  kimi: ['kimi-k2.6', 'kimi-k2.5'],
  qwen: [
    'qwen3.6-max',
    'qwen3.6-plus',
    'qwen3.5',
    'qwen3-coder',
    'qwen-max',
    'qwen-plus',
    'qwen-turbo',
  ],
}

// 各供应商默认 Base URL（OpenAI 兼容接口）。openai/anthropic/custom 走官方端点，留空。
const PROVIDER_BASE_URLS: Record<string, string> = {
  deepseek: 'https://api.deepseek.com',
  glm: 'https://open.bigmodel.cn/api/aihub/v1',
  kimi: 'https://api.moonshot.cn/v1',
  qwen: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
}

interface FormState {
  provider: string
  api_key: string
  model_name: string
  base_url: string
}

const EMPTY_FORM: FormState = {
  provider: 'openai',
  api_key: '',
  model_name: 'gpt-5.5',
  base_url: '',
}

export function SettingsPage() {
  const { t } = useTranslation()
  const [configs, setConfigs] = useState<LLMConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [showApiKey, setShowApiKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const fetchConfigs = useCallback(async () => {
    try {
      const res = await listLLMConfigs()
      if (res.code === 0) {
        setConfigs(res.data)
      } else {
        toast.error(t('settings.loadError', { msg: res.message }))
      }
    } catch {
      toast.error(t('settings.loadErrorGeneric'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    fetchConfigs()
  }, [fetchConfigs])

  function handleProviderChange(provider: string) {
    const models = PROVIDER_MODELS[provider]
    // 切换供应商时预填默认 Base URL（custom / openai / anthropic 留空走官方端点）
    const baseUrl = PROVIDER_BASE_URLS[provider] ?? ''
    setForm((prev) => ({
      ...prev,
      provider,
      model_name: models ? models[0] : '',
      base_url: baseUrl,
    }))
  }

  function handleEdit(config: LLMConfig) {
    setEditingId(config.id)
    setForm({
      provider: config.provider,
      api_key: '',
      model_name: config.model_name,
      base_url: config.base_url ?? '',
    })
    setShowApiKey(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  function handleCancelEdit() {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setShowApiKey(false)
  }

  async function handleTestConnection() {
    if (!form.api_key) {
      toast.error(t('settings.apiKeyRequiredTest'))
      return
    }
    if (!form.model_name) {
      toast.error(t('settings.modelRequiredTest'))
      return
    }

    setTesting(true)
    try {
      const res = await testLLMConnection({
        provider: form.provider,
        api_key: form.api_key,
        model_name: form.model_name,
        base_url: form.base_url || undefined,
      })
      if (res.code === 0 && res.data.success) {
        const modelCount = res.data.models?.length
        toast.success(
          modelCount
            ? t('settings.connectionSuccessModels', { count: modelCount })
            : t('settings.connectionSuccess'),
        )
      } else {
        toast.error(res.data?.error ?? res.message ?? t('settings.testErrorGeneric'))
      }
    } catch {
      toast.error(t('settings.testErrorGeneric'))
    } finally {
      setTesting(false)
    }
  }

  async function handleSave() {
    if (!form.api_key && !editingId) {
      toast.error(t('settings.apiKeyRequired'))
      return
    }
    if (!form.model_name) {
      toast.error(t('settings.modelRequired'))
      return
    }
    if (form.provider === 'custom' && !form.base_url) {
      toast.error(t('settings.baseUrlRequired'))
      return
    }

    setSaving(true)
    try {
      const payload = {
        provider: form.provider,
        api_key: form.api_key,
        model_name: form.model_name,
        base_url: form.base_url || null,
      }

      if (editingId) {
        const updatePayload: Record<string, string | null | undefined> = {
          provider: form.provider,
          model_name: form.model_name,
          base_url: form.base_url || null,
        }
        if (form.api_key) {
          updatePayload.api_key = form.api_key
        }
        const res = await updateLLMConfig(editingId, updatePayload)
        if (res.code === 0) {
          toast.success(t('settings.updated'))
          setEditingId(null)
          setForm(EMPTY_FORM)
          setShowApiKey(false)
          await fetchConfigs()
        } else {
          toast.error(t('settings.updateError', { msg: res.message }))
        }
      } else {
        const res = await createLLMConfig(payload)
        if (res.code === 0) {
          toast.success(t('settings.saved'))
          setForm(EMPTY_FORM)
          setShowApiKey(false)
          await fetchConfigs()
        } else {
          toast.error(t('settings.saveError', { msg: res.message }))
        }
      }
    } catch {
      toast.error(t('settings.saveErrorGeneric'))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id)
    try {
      const res = await deleteLLMConfig(id)
      if (res.code === 0) {
        toast.success(t('settings.deleted'))
        if (editingId === id) {
          setEditingId(null)
          setForm(EMPTY_FORM)
        }
        await fetchConfigs()
      } else {
        toast.error(t('settings.deleteError', { msg: res.message }))
      }
    } catch {
      toast.error(t('settings.deleteErrorGeneric'))
    } finally {
      setDeletingId(null)
    }
  }

  const isCustomProvider = form.provider === 'custom'
  const modelOptions = PROVIDER_MODELS[form.provider]

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-3xl font-black">{t('settings.title')}</h1>
        <p className="mt-1 text-muted-foreground">{t('settings.subtitle')}</p>
      </div>

      {/* Config Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl font-black">
            {editingId ? (
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
            {editingId ? t('settings.editDesc') : t('settings.addDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Provider */}
          <div className="space-y-2">
            <Label htmlFor="provider" className="font-bold">
              {t('settings.provider')}
            </Label>
            <Select value={form.provider} onValueChange={handleProviderChange}>
              <SelectTrigger id="provider">
                <SelectValue placeholder={t('settings.provider')} />
              </SelectTrigger>
              <SelectContent>
                {PROVIDERS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {PROVIDER_LABELS[p]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Model */}
          <div className="space-y-2">
            <Label htmlFor="model" className="font-bold">
              {t('settings.model')}
            </Label>
            <Input
              id="model"
              placeholder={
                isCustomProvider
                  ? t('settings.customModelPlaceholder')
                  : t('settings.modelPlaceholder')
              }
              value={form.model_name}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  model_name: e.target.value,
                }))
              }
            />
            {modelOptions && modelOptions.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {modelOptions.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() =>
                      setForm((prev) => ({ ...prev, model_name: m }))
                    }
                    className={`rounded-base border-2 px-2.5 py-1 text-xs font-bold transition-colors ${
                      form.model_name === m
                        ? 'border-border bg-main text-main-foreground'
                        : 'border-border bg-secondary-background hover:bg-main/20'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <Label htmlFor="api_key" className="font-bold">
              {t('settings.apiKey')}
            </Label>
            <div className="relative">
              <Input
                id="api_key"
                type={showApiKey ? 'text' : 'password'}
                placeholder={
                  editingId
                    ? t('settings.apiKeyKeep')
                    : t('settings.apiKeyPlaceholder')
                }
                value={form.api_key}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, api_key: e.target.value }))
                }
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowApiKey((prev) => !prev)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-foreground/60 hover:text-foreground"
                aria-label={showApiKey ? t('settings.hideApiKey') : t('settings.showApiKey')}
              >
                {showApiKey ? (
                  <EyeOff className="size-4" />
                ) : (
                  <Eye className="size-4" />
                )}
              </button>
            </div>
          </div>

          {/* Base URL */}
          <div className="space-y-2">
            <Label htmlFor="base_url" className="font-bold">
              {t('settings.baseUrl')}{' '}
              {isCustomProvider ? (
                <span className="text-red-500">*</span>
              ) : (
                <span className="text-foreground/50 font-normal">
                  {t('settings.baseUrlOptional')}
                </span>
              )}
            </Label>
            <Input
              id="base_url"
              placeholder={t('settings.baseUrlPlaceholder')}
              value={form.base_url}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, base_url: e.target.value }))
              }
            />
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3 pt-2">
            <Button
              onClick={handleTestConnection}
              variant="neutral"
              disabled={testing || !form.api_key}
            >
              {testing ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <FlaskConical className="size-4" />
              )}
              {testing ? t('settings.testing') : t('settings.test')}
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Save className="size-4" />
              )}
              {saving
                ? t('common.loading')
                : editingId
                  ? t('settings.updateConfig')
                  : t('settings.saveConfig')}
            </Button>
            {editingId && (
              <Button variant="neutral" onClick={handleCancelEdit}>
                <X className="size-4" />
                {t('common.cancel')}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Saved Configs List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-black">
            {t('settings.savedConfigs')}
          </CardTitle>
          <CardDescription>
            {configs.length === 0 && !loading
              ? t('settings.noConfigs')
              : t('settings.configsCount', { count: configs.length })}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
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
                  className="flex flex-col gap-3 rounded-base border-2 border-border bg-secondary-background p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex flex-col gap-1.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold">
                        {PROVIDER_LABELS[config.provider] ?? config.provider}
                      </span>
                      <Badge variant="neutral">{config.model_name}</Badge>
                      {config.is_active && <Badge>{t('common.active')}</Badge>}
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
                      variant="neutral"
                      onClick={() => handleEdit(config)}
                    >
                      <Pencil className="size-3.5" />
                      {t('common.edit')}
                    </Button>
                    <Button
                      size="sm"
                      variant="neutral"
                      disabled={deletingId === config.id}
                      onClick={() => {
                        if (
                          window.confirm(t('settings.deleteConfirm'))
                        ) {
                          handleDelete(config.id)
                        }
                      }}
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
  )
}
