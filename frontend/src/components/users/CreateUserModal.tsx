import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createUser } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { UserPlus } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'


const schema = z.object({
  display_name: z.string().min(1, '顯示名稱為必填'),
  email: z.string().min(1, 'Email 為必填').email('請輸入有效的 Email'),
  role: z.enum(['user', 'admin'] as const),
})
type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  required,
  children,
}: {
  label: string
  error?: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="ml-1 text-destructive">*</span>}
      </label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

export default function CreateUserModal() {
  const [open, setOpen] = useState(false)
  const [inviteToken, setInviteToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { display_name: '', email: '', role: 'user' },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) => createUser(values),
    onSuccess: (data) => {
      setInviteToken(data.invite_token)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    },
    onError: (err: Error) => {
      toast({ title: err.message || '建立失敗', variant: 'destructive' })
    },
  })

  function handleClose() {
    setOpen(false)
    setInviteToken(null)
    setCopied(false)
    reset()
  }

  const inviteUrl = inviteToken
    ? `${window.location.origin}/invite/${inviteToken}`
    : ''

  function copyToClipboard() {
    function doFallback() {
      const el = document.createElement('textarea')
      el.value = inviteUrl
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(true)
    }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(inviteUrl).then(() => setCopied(true)).catch(doFallback)
    } else {
      doFallback()
    }
  }

  return (
    <>
      <Button onClick={() => setOpen(true)}>
        <UserPlus className="mr-2 size-4" />
        新增使用者
      </Button>
      <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); else setOpen(true) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{inviteToken ? '邀請連結已產生' : '新增使用者'}</DialogTitle>
          </DialogHeader>

          {inviteToken ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                請將以下連結傳送給使用者，連結有效期為 7 天。
              </p>
              <div className="flex gap-2">
                <Input readOnly value={inviteUrl} className="text-xs" />
                <Button variant="outline" onClick={copyToClipboard}>
                  {copied ? '已複製' : '複製'}
                </Button>
              </div>
              <Button className="w-full" onClick={handleClose}>
                關閉
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
              <Field label="顯示名稱" error={errors.display_name?.message} required>
                <Input {...register('display_name')} placeholder="王小明" />
              </Field>
              <Field label="Email" error={errors.email?.message} required>
                <Input type="email" {...register('email')} placeholder="user@corp.com" />
              </Field>
              <Field label="角色" error={errors.role?.message} required>
                <Select
                  defaultValue="user"
                  onValueChange={(v) =>
                    setValue('role', v as 'user' | 'admin', { shouldValidate: true })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="user">一般使用者</SelectItem>
                    <SelectItem value="admin">管理員</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              <Button type="submit" className="w-full" disabled={isPending}>
                {isPending ? '建立中...' : '建立並產生邀請連結'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </>
  )
}
