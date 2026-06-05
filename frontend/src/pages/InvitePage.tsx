import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { validateInvite, acceptInvite } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const schema = z
  .object({
    password: z.string().min(8, '密碼至少 8 個字元'),
    confirm_password: z.string().min(1, '請確認密碼'),
  })
  .refine((v) => v.password === v.confirm_password, {
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

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const [done, setDone] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['invite', token],
    queryFn: () => validateInvite(token!),
    retry: false,
  })

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const { mutate, isPending, isError: submitError, error: submitErr } = useMutation({
    mutationFn: (values: FormValues) => acceptInvite(token!, values.password),
    onSuccess: () => {
      setDone(true)
      setTimeout(() => { window.location.href = '/login' }, 2000)
    },
  })

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        驗證中...
      </div>
    )
  }

  if (done) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>密碼設定成功</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">正在導向登入頁面...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <Card className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>邀請連結無效</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              此邀請連結已失效或過期，請聯絡管理員重新產生。
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>設定密碼</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs text-muted-foreground">帳號</p>
            <p className="font-medium">{data.email}</p>
          </div>
          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <Field label="密碼" error={errors.password?.message}>
              <Input type="password" {...register('password')} />
            </Field>
            <Field label="確認密碼" error={errors.confirm_password?.message}>
              <Input type="password" {...register('confirm_password')} />
            </Field>
            {submitError && (
              <p className="text-sm text-destructive">
                {(submitErr as Error)?.message || '設定失敗，請稍後再試'}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '設定中...' : '設定密碼'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
