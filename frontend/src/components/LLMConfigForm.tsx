import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Eye,
  EyeOff,
  FlaskConical,
  Save,
  Loader2,
  X,
  CircleCheck,
  CircleAlert,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

import {
  createLLMConfig,
  updateLLMConfig,
  testLLMConnection,
} from '@/api/settings'
import {
  PROVIDERS,
  PROVIDER_LABELS,
  PROVIDER_MODELS,
  PROVIDER_BASE_URLS,
} from '@/lib/llm-providers'
import { useSettingsStore } from '@/stores/settingsStore'
import type { LLMConfig } from '@/types/settings'

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

/** 表单内联反馈：紧贴操作按钮显示，替代距离操作区过远的全局 toast */
interface FormFeedback {
  kind: 'success' | 'error'
  message: string
}

interface LLMConfigFormProps {
  /** 传入已保存配置进入编辑模式；为空则是新建模式 */
  editingConfig?: LLMConfig | null
  /** 保存（并自动验证）完成后的回调，verified 表示验证是否通过 */
  onSaved?: (config: LLMConfig, verified: boolean) => void
  /** 编辑模式下点击取消 */
  onCancelEdit?: () => void
}

export function LLMConfigForm({ editingConfig, onSaved, onCancelEdit }: LLMConfigFormProps) {
  const { t } = useTranslation()
  const refreshSettings = useSettingsStore((s) => s.refresh)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [showApiKey, setShowApiKey] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<FormFeedback | null>(null)
  // 测试连接成功后从供应商实测获取的可用模型列表（models.list 结果）
  const [liveModels, setLiveModels] = useState<string[]>([])

  // 切换新建/编辑目标时重置表单（编辑时 API Key 留空表示保留原密钥）
  useEffect(() => {
    if (editingConfig) {
      setForm({
        provider: editingConfig.provider,
        api_key: '',
        model_name: editingConfig.model_name,
        base_url: editingConfig.base_url ?? '',
      })
    } else {
      setForm(EMPTY_FORM)
    }
    setShowApiKey(false)
    setFeedback(null)
    setLiveModels([])
  }, [editingConfig])

  function handleProviderChange(provider: string) {
    const models = PROVIDER_MODELS[provider]
    // 切换供应商时预填默认 Base URL（custom / openai / anthropic 留空走官方端点）
    const baseUrl = PROVIDER_BASE_URLS[provider] ?? ''
    // 实测模型列表与供应商绑定，切换后不再适用
    setLiveModels([])
    setForm((prev) => ({
      ...prev,
      provider,
      model_name: models ? models[0] : '',
      base_url: baseUrl,
    }))
  }

  async function handleTestConnection() {
    if (!form.api_key && !editingConfig) {
      setFeedback({ kind: 'error', message: t('settings.apiKeyRequiredTest') })
      return
    }
    if (!form.model_name) {
      setFeedback({ kind: 'error', message: t('settings.modelRequiredTest') })
      return
    }

    setFeedback(null)
    setTesting(true)
    try {
      const res = await testLLMConnection({
        provider: form.provider,
        // 编辑模式下未重填 Key 时省略，后端使用已保存的 Key 测试
        api_key: form.api_key || undefined,
        model_name: form.model_name,
        base_url: form.base_url || undefined,
        config_id: editingConfig?.id,
      })
      if (res.code === 0 && res.data.success) {
        const models = res.data.models ?? []
        // 将实测可用模型并入模型选择区，供用户点选
        setLiveModels(models.filter(Boolean))
        setFeedback({
          kind: 'success',
          message: models.length
            ? t('settings.connectionSuccessModels', { count: models.length })
            : t('settings.connectionSuccess'),
        })
        if (editingConfig) await refreshSettings()
      } else {
        setFeedback({
          kind: 'error',
          // code=0 时信封 message 恒为 success，只取业务错误；用 || 兜底空字符串（如后端超时）
          message:
            (res.code === 0 ? res.data?.error : res.message) ||
            t('settings.testErrorGeneric'),
        })
        if (editingConfig) await refreshSettings()
      }
    } catch {
      setFeedback({ kind: 'error', message: t('settings.testErrorGeneric') })
    } finally {
      setTesting(false)
    }
  }

  /** 保存后自动带 config_id 触发一次连接测试，通过即标记 verified */
  async function verifyConfig(config: LLMConfig): Promise<boolean> {
    try {
      const res = await testLLMConnection({
        provider: config.provider,
        api_key: form.api_key || undefined,
        model_name: config.model_name,
        base_url: config.base_url || undefined,
        config_id: config.id,
      })
      if (res.code === 0 && res.data.success) {
        // 成功提示由调用方决定（弹窗关闭后 toast / 设置页内联展示）
        setFeedback({ kind: 'success', message: t('settings.verifiedAndReady') })
        return true
      }
      setFeedback({
        kind: 'error',
        message: t('settings.verifyFailed', {
          msg:
            (res.code === 0 ? res.data?.error : res.message) ||
            t('settings.testErrorGeneric'),
        }),
      })
      return false
    } catch {
      setFeedback({
        kind: 'error',
        message: t('settings.verifyFailed', { msg: t('settings.testErrorGeneric') }),
      })
      return false
    }
  }

  async function handleSave() {
    if (!form.api_key && !editingConfig) {
      setFeedback({ kind: 'error', message: t('settings.apiKeyRequired') })
      return
    }
    if (!form.model_name) {
      setFeedback({ kind: 'error', message: t('settings.modelRequired') })
      return
    }
    if (form.provider === 'custom' && !form.base_url) {
      setFeedback({ kind: 'error', message: t('settings.baseUrlRequired') })
      return
    }

    setFeedback(null)
    setSaving(true)
    try {
      let saved: LLMConfig | null = null

      if (editingConfig) {
        const updatePayload: Record<string, string | null | undefined> = {
          provider: form.provider,
          model_name: form.model_name,
          base_url: form.base_url || null,
        }
        if (form.api_key) {
          updatePayload.api_key = form.api_key
        }
        const res = await updateLLMConfig(editingConfig.id, updatePayload)
        if (res.code === 0) {
          saved = res.data
        } else {
          setFeedback({
            kind: 'error',
            message: t('settings.updateError', { msg: res.message }),
          })
        }
      } else {
        const res = await createLLMConfig({
          provider: form.provider,
          api_key: form.api_key,
          model_name: form.model_name,
          base_url: form.base_url || null,
        })
        if (res.code === 0) {
          saved = res.data
        } else {
          setFeedback({
            kind: 'error',
            message: t('settings.saveError', { msg: res.message }),
          })
        }
      }

      if (saved) {
        // 保存即验证：验证结果决定上传门禁是否放行
        const verified = await verifyConfig(saved)
        setForm(EMPTY_FORM)
        setShowApiKey(false)
        await refreshSettings()
        onSaved?.(saved, verified)
      }
    } catch {
      setFeedback({ kind: 'error', message: t('settings.saveErrorGeneric') })
    } finally {
      setSaving(false)
    }
  }

  const isCustomProvider = form.provider === 'custom'
  const modelOptions = PROVIDER_MODELS[form.provider]

  return (
    <div className="space-y-5">
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
        {/* 测试连接成功后从供应商实测获取的模型，点选即填入 */}
        {liveModels.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-bold text-foreground/60">
              {t('settings.liveModels')}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {liveModels.map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() =>
                    setForm((prev) => ({ ...prev, model_name: m }))
                  }
                  className={`rounded-base border-2 px-2.5 py-1 text-xs font-bold transition-colors ${
                    form.model_name === m
                      ? 'border-border bg-main text-main-foreground'
                      : 'border-border bg-background hover:bg-main/20'
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
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
              editingConfig
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
          disabled={testing || (!form.api_key && !editingConfig)}
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
            : editingConfig
              ? t('settings.updateConfig')
              : t('settings.saveConfig')}
        </Button>
        {editingConfig && onCancelEdit && (
          <Button variant="neutral" onClick={onCancelEdit}>
            <X className="size-4" />
            {t('common.cancel')}
          </Button>
        )}
      </div>

      {/* 内联反馈：紧贴操作按钮，复用统一 Alert 组件（成功=default，错误=destructive） */}
      {feedback && (
        <Alert
          variant={feedback.kind === 'error' ? 'destructive' : 'default'}
          role={feedback.kind === 'error' ? 'alert' : 'status'}
        >
          {feedback.kind === 'success' ? (
            <CircleCheck />
          ) : (
            <CircleAlert />
          )}
          <AlertDescription className="break-all font-bold">
            {feedback.message}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
