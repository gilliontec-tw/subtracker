import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listGroups, deleteGroup } from '@/api/groups'
import type { Group } from '@/types/api'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { useToast } from '@/hooks/use-toast'
import { Trash2, Users } from 'lucide-react'
import CreateGroupDialog from '@/components/groups/CreateGroupDialog'
import GroupMembersDialog from '@/components/groups/GroupMembersDialog'

export default function GroupsPage() {
  const [createOpen, setCreateOpen] = useState(false)
  const [managingGroup, setManagingGroup] = useState<Group | null>(null)
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { data: groups = [], isLoading } = useQuery({
    queryKey: ['groups'],
    queryFn: listGroups,
  })

  const { mutate: remove } = useMutation({
    mutationFn: deleteGroup,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      toast({ title: '群組已刪除' })
    },
    onError: (err: Error) => toast({ title: err.message, variant: 'destructive' }),
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">群組管理</h1>
        <Button onClick={() => setCreateOpen(true)}>新增群組</Button>
      </div>

      {isLoading ? (
        <p className="text-muted-foreground">載入中...</p>
      ) : (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>群組名稱</TableHead>
                <TableHead className="w-32 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={2}
                    className="text-center text-muted-foreground py-8"
                  >
                    尚無群組
                  </TableCell>
                </TableRow>
              ) : (
                groups.map((group) => (
                  <TableRow key={group.id}>
                    <TableCell className="font-medium">{group.name}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setManagingGroup(group)}
                        title="管理成員"
                      >
                        <Users className="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => remove(group.id)}
                        title="刪除群組"
                      >
                        <Trash2 className="size-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      <CreateGroupDialog open={createOpen} onOpenChange={setCreateOpen} />
      <GroupMembersDialog
        group={managingGroup}
        onOpenChange={(open) => {
          if (!open) setManagingGroup(null)
        }}
      />
    </div>
  )
}
