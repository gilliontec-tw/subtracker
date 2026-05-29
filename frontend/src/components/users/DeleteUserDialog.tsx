import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteUser } from '@/api/users'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Trash2 } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface Props {
  userId: number
  displayName: string
}

export default function DeleteUserDialog({ userId, displayName }: Props) {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { mutate, isPending } = useMutation({
    mutationFn: () => deleteUser(userId),
    onSuccess: () => {
      setOpen(false)
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast({ title: `「${displayName}」已刪除` })
    },
    onError: (err: Error) => {
      toast({ title: err.message || '刪除失敗', variant: 'destructive' })
    },
  })

  return (
    <>
      <Button variant="ghost" size="icon" onClick={() => setOpen(true)}>
        <Trash2 className="size-4 text-destructive" />
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>確認刪除</DialogTitle>
            <DialogDescription>
              確定要刪除「{displayName}」嗎？此操作無法復原。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)} disabled={isPending}>
              取消
            </Button>
            <Button variant="destructive" onClick={() => mutate()} disabled={isPending}>
              {isPending ? '刪除中...' : '確認刪除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
