import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { forgotPassword } from '@/api/auth'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import AuthLayout from '@/layouts/AuthLayout'

const schema = z.object({
  email: z.string().email('請輸入有效的 Email'),
})
type FormValues = z.infer<typeof schema>

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) => forgotPassword(values.email),
    onSuccess: () => setSent(true),
    onError: () => setSent(true), // 不洩露 email 是否存在
  })

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle className="text-center text-xl">忘記密碼</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {sent ? (
            <>
              <p className="text-sm text-muted-foreground">
                若此 Email 已註冊，重設連結已寄出，請查收信箱（含垃圾郵件）。
              </p>
              <Link
                to="/login"
                className="block text-center text-sm text-primary underline-offset-4 hover:underline"
              >
                返回登入
              </Link>
            </>
          ) : (
            <>
              <p className="text-sm text-muted-foreground">
                輸入您的帳號 Email，我們將寄送密碼重設連結。
              </p>
              <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
                <div className="space-y-1">
                  <label htmlFor="email" className="text-sm font-medium">
                    Email
                  </label>
                  <Input
                    id="email"
                    type="email"
                    autoComplete="email"
                    placeholder="user@example.com"
                    {...register('email')}
                  />
                  {errors.email && (
                    <p className="text-xs text-destructive">{errors.email.message}</p>
                  )}
                </div>
                <Button type="submit" className="w-full" disabled={isPending}>
                  {isPending ? '寄送中...' : '寄送重設連結'}
                </Button>
              </form>
              <Link
                to="/login"
                className="block text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
              >
                返回登入
              </Link>
            </>
          )}
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
