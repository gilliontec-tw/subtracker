import { Navigate, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation } from '@tanstack/react-query'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'
import AuthLayout from '@/layouts/AuthLayout'

const schema = z.object({
  email: z.string().min(1, '請輸入 Email'),
  password: z.string().min(1, '請輸入密碼'),
})

type FormValues = z.infer<typeof schema>

export default function LoginPage() {
  const navigate = useNavigate()
  const { currentUser, setUser } = useAuthStore()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) })

  const { mutate, isPending } = useMutation({
    mutationFn: ({ email, password }: FormValues) => login(email, password),
    onSuccess: (user) => {
      setUser(user)
      navigate('/dashboard', { replace: true })
    },
    onError: () => {
      toast({ title: '登入失敗', description: '帳號或密碼錯誤', variant: 'destructive' })
    },
  })

  if (currentUser) return <Navigate to="/subscriptions" replace />

  return (
    <AuthLayout>
      <Card>
        <CardHeader>
          <CardTitle className="text-center text-xl">SubTrack 登入</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit((data) => mutate(data))} className="space-y-4">
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
              {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
            </div>
            <div className="space-y-1">
              <label htmlFor="password" className="text-sm font-medium">
                密碼
              </label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register('password')}
              />
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '登入中...' : '登入'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
