import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listGroupMembers, addGroupMember, removeGroupMember } from '@/api/groups'
import { listUsers } from '@/api/users'
import type { Group } from '@/types/api'
import { Button } from '@/components/ui/button'
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
import { useToast } from '@/hooks/use-toast'
import { X } from 'lucide-react'

interface Props {
  group: Group | null
  onOpenChange: (open: boolean) => void
}

export default function GroupMembersDialog({ group, onOpenChange }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  const [selectedUserId, setSelectedUserId] = useState<string>('')

  const { data: members = [] } = useQuery({
    queryKey: ['group-members', group?.id],
    queryFn: () => listGroupMembers(group!.id),
    enabled: group !== null,
  })

  const { data: allUsers = [] } = useQuery({
    queryKey: ['users'],
    queryFn: listUsers,
    enabled: group !== null,
  })

  const memberIds = new Set(members.map((m) => m.id))
  const nonMembers = allUsers.filter((u) => !memberIds.has(u.id) && u.is_active)

  const { mutate: addMember, isPending: isAdding } = useMutation({
    mutationFn: (userId: number) => addGroupMember(group!.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group-members', group?.id] })
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setSelectedUserId('')
      toast({ title: '成員已加入' })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  const { mutate: removeMember } = useMutation({
    mutationFn: (userId: number) => removeGroupMember(group!.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['group-members', group?.id] })
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast({ title: '成員已移除' })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  return (
    <Dialog open={group !== null} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{group?.name} — 成員管理</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex gap-2">
            <Select value={selectedUserId} onValueChange={setSelectedUserId}>
              <SelectTrigger className="flex-1">
                <SelectValue placeholder="選擇要加入的使用者" />
              </SelectTrigger>
              <SelectContent>
                {nonMembers.map((u) => (
                  <SelectItem key={u.id} value={String(u.id)}>
                    {u.display_name} ({u.email})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              onClick={() => selectedUserId && addMember(parseInt(selectedUserId))}
              disabled={!selectedUserId || isAdding}
            >
              加入
            </Button>
          </div>

          <div className="space-y-2">
            {members.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                此群組尚無成員
              </p>
            ) : (
              members.map((m) => (
                <div
                  key={m.id}
                  className="flex items-center justify-between rounded border px-3 py-2"
                >
                  <div>
                    <span className="text-sm font-medium">{m.display_name}</span>
                    <span className="ml-2 text-xs text-muted-foreground">{m.email}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeMember(m.id)}
                  >
                    <X className="size-4" />
                  </Button>
                </div>
              ))
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
