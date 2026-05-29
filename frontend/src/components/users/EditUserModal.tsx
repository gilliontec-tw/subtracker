import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { updateUser, toggleUserStatus } from '@/api/users'
import type { UserDetail } from '@/types/api'
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
import { Pencil } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

const schema = z.object({
  display_name: z.string().min(1, '顯示名稱為必填'),
  role: z.enum(['user', 'admin'] as const),
  is_active: z.enum(['active', 'inactive'] as const),
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
  user: UserDetail
}

export default function EditUserModal({ user }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      display_name: user.display_name,
      role: user.role,
      is_active: user.is_active ? 'active' : 'inactive',
    },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: async (values: FormValues) => {
      const newIsActive = values.is_active === 'active'
      await updateUser(user.id, { display_name: values.display_name, role: values.role })
      if (newIsActive !== user.is_active) {
        await toggleUserStatus(user.id, newIsActive)
      }
    },
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast({ title: '使用者已更新' })
    },
    onError: (err: Error) => {
      toast({ title: err.message || '更新失敗', variant: 'destructive' })
    },
  })

  return (
    <>
      <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
        <Pencil className="size-4" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>編輯使用者</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
            <Field label="顯示名稱" error={errors.display_name?.message}>
              <Input {...register('display_name')} />
            </Field>
            <Field label="角色" error={errors.role?.message}>
              <Select
                defaultValue={user.role}
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
            <Field label="狀態">
              <Select
                defaultValue={user.is_active ? 'active' : 'inactive'}
                onValueChange={(v) =>
                  setValue('is_active', v as 'active' | 'inactive', { shouldValidate: true })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">啟用中</SelectItem>
                  <SelectItem value="inactive">已停用</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '儲存中...' : '儲存'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
