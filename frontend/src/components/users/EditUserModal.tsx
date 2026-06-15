import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { updateUser, toggleUserStatus } from '@/api/users'
import { listGroups, addGroupMember, removeGroupMember, getUserGroups } from '@/api/groups'
import type { UserDetail } from '@/types/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
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
import { Pencil, X } from 'lucide-react'
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
  const [addGroupId, setAddGroupId] = useState<string>('')
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

  const { data: allGroups = [] } = useQuery({
    queryKey: ['groups'],
    queryFn: listGroups,
    enabled: open,
  })

  const { data: userGroups = [], refetch: refetchUserGroups } = useQuery({
    queryKey: ['user-groups', user.id],
    queryFn: () => getUserGroups(user.id),
    enabled: open,
  })

  const userGroupIds = new Set(userGroups.map((g) => g.id))
  const availableGroups = allGroups.filter((g) => !userGroupIds.has(g.id))

  const { mutate: addToGroup, isPending: isAdding } = useMutation({
    mutationFn: (groupId: number) => addGroupMember(groupId, user.id),
    onSuccess: () => {
      void refetchUserGroups()
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setAddGroupId('')
      toast({ title: '已加入群組' })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  const { mutate: removeFromGroup } = useMutation({
    mutationFn: (groupId: number) => removeGroupMember(groupId, user.id),
    onSuccess: () => {
      void refetchUserGroups()
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast({ title: '已移出群組' })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  useEffect(() => {
    if (open) {
      reset({
        display_name: user.display_name,
        role: user.role,
        is_active: user.is_active ? 'active' : 'inactive',
      })
    }
  }, [open, user, reset])

  return (
    <>
      <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
        <Pencil className="size-4" />
      </Button>
      <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) setAddGroupId('') }}>
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
            {/* Group membership */}
            <div className="space-y-2">
              <label className="text-sm font-medium">所屬群組</label>
              <div className="flex flex-wrap gap-1 min-h-8">
                {userGroups.map((g) => (
                  <Badge key={g.id} variant="secondary" className="gap-1">
                    {g.name}
                    <button
                      type="button"
                      onClick={() => removeFromGroup(g.id)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="size-3" />
                    </button>
                  </Badge>
                ))}
                {userGroups.length === 0 && (
                  <span className="text-xs text-muted-foreground">尚未加入任何群組</span>
                )}
              </div>
              {availableGroups.length > 0 && (
                <div className="flex gap-2">
                  <Select value={addGroupId} onValueChange={setAddGroupId}>
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="加入群組..." />
                    </SelectTrigger>
                    <SelectContent>
                      {availableGroups.map((g) => (
                        <SelectItem key={g.id} value={String(g.id)}>
                          {g.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => addGroupId && addToGroup(parseInt(addGroupId))}
                    disabled={!addGroupId || isAdding}
                  >
                    加入
                  </Button>
                </div>
              )}
            </div>
            <Button type="submit" className="w-full" disabled={isPending}>
              {isPending ? '儲存中...' : '儲存'}
            </Button>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
