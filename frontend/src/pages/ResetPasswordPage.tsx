import { useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { validateInvite, acceptInvite } from '@/api/users'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import AuthLayout from '@/layouts/AuthLayout'

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

export default function ResetPasswordPage() {
  const { token } = useParams<{ token: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [done, setDone] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['reset-password', token],
    queryFn: () => validateInvite(token!),
    retry: false,
  })

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending, isError: submitError, error: submitErr } = useMutation({
    mutationFn: (values: FormValues) => acceptInvite(token!, values.password),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ['reset-password', token] })
      setDone(true)
      setTimeout(() => navigate('/login', { replace: true }), 2000)
    },
  })

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        驗證中...
      </div>
    )
  }

  if (isError || !data) {
    return (
      <AuthLayout>
        <Card>
          <CardHeader>
            <CardTitle>重設連結無效</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              此重設連結已失效或過期（有效期 1 小時），請重新申請。
            </p>
            <Link
              to="/forgot-password"
              className="block text-center text-sm text-primary underline-offset-4 hover:underline"
            >
              重新申請重設密碼
            </Link>
          </CardContent>
        </Card>
      </AuthLayout>
    )
  }

  if (done) {
    return (
      <AuthLayout>
        <Card>
          <CardHeader>
            <CardTitle>密碼重設成功</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">正在導向登入頁面...</p>
          </CardContent>
        </Card>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle>重設密碼</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs text-muted-foreground">帳號</p>
            <p className="font-medium">{data.email}</p>
          </div>
          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <Field label="新密碼" error={errors.password?.message}>
              <Input type="password" autoComplete="new-password" {...register('password')} />
            </Field>
            <Field label="確認新密碼" error={errors.confirm_password?.message}>
              <Input
                type="password"
                autoComplete="new-password"
                {...register('confirm_password')}
              />
            </Field>
            {submitError && (
              <p className="text-sm text-destructive">
                {(submitErr as Error)?.message || '重設失敗，請稍後再試'}
              </p>
            )}
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '重設中...' : '確認重設密碼'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
