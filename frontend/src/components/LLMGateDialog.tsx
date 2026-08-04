import { Link } from 'react-router'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { TriangleAlert } from 'lucide-react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { LLMConfigForm } from '@/components/LLMConfigForm'

interface LLMGateDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** 场景化说明文案，缺省为上传页文案 */
  description?: string
  /** 配置验证通过后的成功提示，缺省为上传页文案 */
  successMessage?: string
}

/**
 * LLM 配置门禁弹窗：未检测到"已激活且已验证"的 LLM 配置时，
 * 拦截上传动作并内嵌配置表单，引导用户就地完成配置与验证。
 */
export function LLMGateDialog({
  open,
  onOpenChange,
  description,
  successMessage,
}: LLMGateDialogProps) {
  const { t } = useTranslation()

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl font-black">
            <TriangleAlert className="size-5 text-red-500" />
            {t('llmGate.title')}
          </DialogTitle>
          <DialogDescription>{description ?? t('llmGate.description')}</DialogDescription>
        </DialogHeader>

        <LLMConfigForm
          onSaved={(_config, verified) => {
            if (verified) {
              // 验证通过即解锁，关闭弹窗引导用户继续
              toast.success(successMessage ?? t('llmGate.readyToUpload'))
              onOpenChange(false)
            }
          }}
        />

        <p className="text-sm text-foreground/60">
          {t('llmGate.settingsHint')}{' '}
          <Link
            to="/settings"
            className="font-bold underline"
            onClick={() => onOpenChange(false)}
          >
            {t('llmGate.goToSettings')}
          </Link>
        </p>
      </DialogContent>
    </Dialog>
  )
}
