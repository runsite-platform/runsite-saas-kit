import { Check, Copy } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const COPIED_FEEDBACK_MILLISECONDS = 2000

interface CopyLinkFieldProps {
  label: string
  value: string
}

export function CopyLinkField({ label, value }: CopyLinkFieldProps) {
  const { t } = useTranslation('organizations')
  const inputId = useId()
  const inputRef = useRef<HTMLInputElement>(null)
  const [isCopied, setIsCopied] = useState(false)

  useEffect(() => {
    if (!isCopied) {
      return
    }
    const resetTimer = window.setTimeout(() => setIsCopied(false), COPIED_FEEDBACK_MILLISECONDS)
    return () => window.clearTimeout(resetTimer)
  }, [isCopied])

  async function copyValue() {
    try {
      await navigator.clipboard.writeText(value)
      setIsCopied(true)
    } catch {
      inputRef.current?.select()
    }
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={inputId}>{label}</Label>
      <div className="flex gap-2">
        <Input
          ref={inputRef}
          id={inputId}
          readOnly
          value={value}
          className="font-mono text-xs"
          onFocus={(event) => event.currentTarget.select()}
        />
        <Button type="button" variant="outline" onClick={() => void copyValue()}>
          {isCopied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
          <span aria-live="polite">{isCopied ? t('invite.copied') : t('invite.copy')}</span>
        </Button>
      </div>
      <p className="text-xs text-muted-foreground">{t('invite.linkHint')}</p>
    </div>
  )
}
