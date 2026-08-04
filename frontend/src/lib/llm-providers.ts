/**
 * LLM 供应商静态配置：选项列表 / 展示名 / 预置模型 / 默认 Base URL
 * 与后端支持的供应商保持一致（openai / anthropic / deepseek），
 * custom 为自定义 OpenAI 兼容端点（Base URL 必填）。
 */

export const PROVIDERS = ['openai', 'anthropic', 'deepseek', 'custom'] as const

export type Provider = (typeof PROVIDERS)[number]

export const PROVIDER_LABELS: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  deepseek: 'DeepSeek',
  custom: 'Custom (OpenAI Compatible)',
}

/** 各供应商的预置模型；第一个为切换供应商后的默认值，custom 不预置由用户自填 */
export const PROVIDER_MODELS: Record<string, string[]> = {
  openai: ['gpt-5.5', 'gpt-5', 'gpt-4o', 'gpt-4o-mini'],
  anthropic: [
    'claude-sonnet-4-5',
    'claude-opus-4-5',
    'claude-haiku-4-5',
  ],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
}

/** 切换供应商时预填的 Base URL；openai / anthropic / custom 留空走官方端点 */
export const PROVIDER_BASE_URLS: Record<string, string> = {
  deepseek: 'https://api.deepseek.com/v1',
}
