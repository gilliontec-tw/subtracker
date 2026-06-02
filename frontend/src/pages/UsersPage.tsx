import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listUsers, regenerateInvite } from '@/api/users'
import CreateUserModal from '@/components/users/CreateUserModal'
import EditUserModal from '@/components/users/EditUserModal'
import DeleteUserDialog from '@/components/users/DeleteUserDialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useToast } from '@/hooks/use-toast'

export default function UsersPage() {
  const { data: users = [], isLoading } = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
  })
  const { toast } = useToast()
  const [resetToken, setResetToken] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const { mutate: doRegenerate, isPending: isRegenerating } = useMutation({
    mutationFn: (id: number) => regenerateInvite(id),
    onSuccess: (data) => {
      setResetToken(data.invite_token)
      setCopied(false)
    },
    onError: (err: Error) => {
      toast({ title: err.message || '重設連結失敗', variant: 'destructive' })
    },
  })

  const resetUrl = resetToken
    ? `${window.location.origin}/invite/${resetToken}`
    : ''

  async function copyToClipboard() {
    await navigator.clipboard.writeText(resetUrl)
    setCopied(true)
  }

  if (isLoading) {
    return <div className="text-muted-foreground">載入中...</div>
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">使用者管理</h1>
        <CreateUserModal />
      </div>
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>顯示名稱</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>角色</TableHead>
              <TableHead>狀態</TableHead>
              <TableHead>建立日期</TableHead>
              <TableHead className="text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-8 text-center text-muted-foreground">
                  沒有使用者資料
                </TableCell>
              </TableRow>
            )}
            {users.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.display_name}</TableCell>
                <TableCell className="text-muted-foreground">{user.email}</TableCell>
                <TableCell>
                  {user.role === 'admin' ? (
                    <Badge className="border-transparent bg-purple-100 text-purple-800 hover:bg-purple-100">
                      管理員
                    </Badge>
                  ) : (
                    <Badge variant="secondary">一般使用者</Badge>
                  )}
                </TableCell>
                <TableCell>
                  {user.is_active ? (
                    <Badge className="border-transparent bg-green-100 text-green-800 hover:bg-green-100">
                      啟用中
                    </Badge>
                  ) : (
                    <Badge variant="secondary">已停用</Badge>
                  )}
                </TableCell>
                <TableCell>{user.created_at ?? '—'}</TableCell>
                <TableCell className="text-right">
                  <div className="flex justify-end gap-1">
                    {user.is_active && (
                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isRegenerating}
                        onClick={() => doRegenerate(user.id)}
                      >
                        重設連結
                      </Button>
                    )}
                    <EditUserModal user={user} />
                    <DeleteUserDialog userId={user.id} displayName={user.display_name} />
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog
        open={!!resetToken}
        onOpenChange={(v) => { if (!v) { setResetToken(null); setCopied(false) } }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>重設密碼連結</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground">
              請將以下連結傳送給使用者，連結有效期為 7 天。
            </p>
            <div className="flex gap-2">
              <Input readOnly value={resetUrl} className="text-xs" />
              <Button variant="outline" onClick={copyToClipboard}>
                {copied ? '已複製' : '複製'}
              </Button>
            </div>
            <Button className="w-full" onClick={() => { setResetToken(null); setCopied(false) }}>
              關閉
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
