import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
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

const PROVIDERS = ['openai', 'anthropic', 'deepseek', 'custom'] as const

const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  deepseek: 'DeepSeek',
  custom: 'Custom',
}

const PROVIDER_MODELS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o3-mini'],
  anthropic: [
    'claude-sonnet-4-20250514',
    'claude-haiku-4-5-20251001',
    'claude-opus-4-20250514',
  ],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
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
  model_name: 'gpt-4o',
  base_url: '',
}

export function SettingsPage() {
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
        toast.error('Failed to load configs: ' + res.message)
      }
    } catch {
      toast.error('Failed to load LLM configurations')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfigs()
  }, [fetchConfigs])

  function handleProviderChange(provider: string) {
    const models = PROVIDER_MODELS[provider]
    setForm((prev) => ({
      ...prev,
      provider,
      model_name: models ? models[0] : '',
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
      toast.error('API key is required to test connection')
      return
    }
    if (!form.model_name) {
      toast.error('Model name is required to test connection')
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
            ? `Connection successful! ${modelCount} models available.`
            : 'Connection successful!',
        )
      } else {
        toast.error(res.data?.error ?? res.message ?? 'Connection test failed')
      }
    } catch {
      toast.error('Connection test failed. Check your settings.')
    } finally {
      setTesting(false)
    }
  }

  async function handleSave() {
    if (!form.api_key && !editingId) {
      toast.error('API key is required')
      return
    }
    if (!form.model_name) {
      toast.error('Model name is required')
      return
    }
    if (form.provider === 'custom' && !form.base_url) {
      toast.error('Base URL is required for Custom provider')
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
          toast.success('Configuration updated successfully')
          setEditingId(null)
          setForm(EMPTY_FORM)
          setShowApiKey(false)
          await fetchConfigs()
        } else {
          toast.error('Failed to update: ' + res.message)
        }
      } else {
        const res = await createLLMConfig(payload)
        if (res.code === 0) {
          toast.success('Configuration saved successfully')
          setForm(EMPTY_FORM)
          setShowApiKey(false)
          await fetchConfigs()
        } else {
          toast.error('Failed to save: ' + res.message)
        }
      }
    } catch {
      toast.error('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id)
    try {
      const res = await deleteLLMConfig(id)
      if (res.code === 0) {
        toast.success('Configuration deleted')
        if (editingId === id) {
          setEditingId(null)
          setForm(EMPTY_FORM)
        }
        await fetchConfigs()
      } else {
        toast.error('Failed to delete: ' + res.message)
      }
    } catch {
      toast.error('Failed to delete configuration')
    } finally {
      setDeletingId(null)
    }
  }

  const isCustomProvider = form.provider === 'custom'
  const modelOptions = PROVIDER_MODELS[form.provider]

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-3xl font-black">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Configure your LLM providers for AI-powered resume reviews.
        </p>
      </div>

      {/* Config Form */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl font-black">
            {editingId ? (
              <>
                <Pencil className="size-5" />
                Edit Configuration
              </>
            ) : (
              <>
                <Plus className="size-5" />
                Add LLM Configuration
              </>
            )}
          </CardTitle>
          <CardDescription>
            {editingId
              ? 'Update the configuration below. Leave API key empty to keep the existing one.'
              : 'Add a new LLM provider to use for resume reviews.'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Provider */}
          <div className="space-y-2">
            <Label htmlFor="provider" className="font-bold">
              Provider
            </Label>
            <Select value={form.provider} onValueChange={handleProviderChange}>
              <SelectTrigger id="provider">
                <SelectValue placeholder="Select a provider" />
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
              Model
            </Label>
            {isCustomProvider ? (
              <Input
                id="model"
                placeholder="e.g. my-custom-model"
                value={form.model_name}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    model_name: e.target.value,
                  }))
                }
              />
            ) : (
              <Select
                value={form.model_name}
                onValueChange={(val) =>
                  setForm((prev) => ({ ...prev, model_name: val }))
                }
              >
                <SelectTrigger id="model">
                  <SelectValue placeholder="Select a model" />
                </SelectTrigger>
                <SelectContent>
                  {modelOptions?.map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* API Key */}
          <div className="space-y-2">
            <Label htmlFor="api_key" className="font-bold">
              API Key
            </Label>
            <div className="relative">
              <Input
                id="api_key"
                type={showApiKey ? 'text' : 'password'}
                placeholder={
                  editingId
                    ? 'Leave empty to keep existing key'
                    : 'Enter your API key'
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
                aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
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
              Base URL{' '}
              {isCustomProvider ? (
                <span className="text-red-500">*</span>
              ) : (
                <span className="text-foreground/50 font-normal">
                  (optional)
                </span>
              )}
            </Label>
            <Input
              id="base_url"
              placeholder={
                isCustomProvider
                  ? 'https://your-api-endpoint.com/v1'
                  : 'Leave empty to use default'
              }
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
              {testing ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Save className="size-4" />
              )}
              {saving
                ? 'Saving...'
                : editingId
                  ? 'Update Config'
                  : 'Save Config'}
            </Button>
            {editingId && (
              <Button variant="neutral" onClick={handleCancelEdit}>
                <X className="size-4" />
                Cancel
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Saved Configs List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl font-black">
            Saved Configurations
          </CardTitle>
          <CardDescription>
            {configs.length === 0 && !loading
              ? 'No configurations yet. Add one above.'
              : `${configs.length} configuration${configs.length === 1 ? '' : 's'} saved.`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8 text-foreground/50">
              <Loader2 className="mr-2 size-5 animate-spin" />
              Loading configurations...
            </div>
          ) : configs.length === 0 ? (
            <div className="py-8 text-center text-foreground/50">
              No LLM configurations found. Add one using the form above.
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
                      {config.is_active && <Badge>Active</Badge>}
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
                      Edit
                    </Button>
                    <Button
                      size="sm"
                      variant="neutral"
                      disabled={deletingId === config.id}
                      onClick={() => {
                        if (
                          window.confirm(
                            'Are you sure you want to delete this configuration?',
                          )
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
                      Delete
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
