/**
 * pages/InvitePage.tsx — 邀請連結設定密碼頁面（公開頁面，不需登入）
 *
 * 流程：
 *  1. 從 URL 取得 token（/invite/:token）
 *  2. 呼叫 GET /invite/:token 驗證 token 是否有效，取得對應的 email
 *  3. 使用者輸入並確認密碼
 *  4. 呼叫 POST /invite/:token 設定密碼
 *  5. 成功後 2 秒後導向登入頁（用 window.location.href 強制完整重新整理，
 *     確保 authStore 是乾淨的初始狀態）
 *
 * token 來源：管理員建立使用者後取得，或由「重設連結」功能重新產生，有效期 7 天。
 */
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

/** 表單欄位包裝：label + 輸入框 + 錯誤訊息 */
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

  // 驗證 token 是否有效，取得對應 email 用於顯示
  const { data, isLoading } = useQuery({
    queryKey: ['invite', token],
    queryFn: () => validateInvite(token!),
    retry: false, // token 無效就直接顯示失效頁，不重試
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
      // 用 window.location.href 而非 navigate，確保頁面完整重整、authStore 狀態乾淨
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

  // 密碼設定成功的確認畫面
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

  // token 無效或已過期
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
