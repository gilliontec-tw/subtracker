import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createGroup } from '@/api/groups'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'

const schema = z.object({
  name: z.string().min(1, '群組名稱為必填').max(100),
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
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function CreateGroupDialog({ open, onOpenChange }: Props) {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (values: FormValues) => createGroup(values.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['groups'] })
      toast({ title: '群組已建立' })
      onOpenChange(false)
      reset()
    },
    onError: (err: Error) => {
      toast({ title: err.message || '建立失敗', variant: 'destructive' })
    },
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>新增群組</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((v) => mutate(v))} className="space-y-4">
          <Field label="群組名稱" error={errors.name?.message}>
            <Input
              {...register('name')}
              placeholder="例如：MIS、HR、總務"
              autoFocus
            />
          </Field>
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? '建立中...' : '建立'}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}
