import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { resetPasswordDirect } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'

const schema = z
  .object({
    email: z.string().min(1, '請輸入 Email'),
    new_password: z.string().min(8, '密碼至少 8 個字元'),
    confirm_password: z.string().min(1, '請確認密碼'),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    message: '密碼不一致',
    path: ['confirm_password'],
  })

type FormValues = z.infer<typeof schema>

function Field({
  label,
  error,
  children,
}: {
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  )
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function ForgotPasswordDialog({ open, onOpenChange }: Props) {
  const { toast } = useToast()
  const [apiError, setApiError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) =>
      resetPasswordDirect(values.email, values.new_password),
    onSuccess: () => {
      toast({ title: '密碼已重設，請使用新密碼登入' })
      reset()
      setApiError(null)
      onOpenChange(false)
    },
    onError: (err) => {
      const axiosErr = err as { response?: { data?: { message?: string } } }
      const msg =
        axiosErr.response?.data?.message ??
        (err as Error).message ??
        '重設失敗，請稍後再試'
      setApiError(msg)
    },
  })

  function handleOpenChange(val: boolean) {
    if (!val) {
      reset()
      setApiError(null)
    }
    onOpenChange(val)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>重設密碼</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
          <Field label="帳號 (Email)" error={errors.email?.message}>
            <Input
              type="email"
              autoComplete="email"
              placeholder="user@example.com"
              {...register('email')}
            />
          </Field>
          <Field label="新密碼" error={errors.new_password?.message}>
            <Input
              type="password"
              autoComplete="new-password"
              {...register('new_password')}
            />
          </Field>
          <Field label="確認新密碼" error={errors.confirm_password?.message}>
            <Input
              type="password"
              autoComplete="new-password"
              {...register('confirm_password')}
            />
          </Field>
          {apiError && <p className="text-sm text-destructive">{apiError}</p>}
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? '重設中...' : '確認重設'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
