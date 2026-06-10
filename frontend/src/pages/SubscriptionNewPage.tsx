import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createSubscription } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'
import SubscriptionForm from '@/components/subscriptions/SubscriptionForm'

export default function SubscriptionNewPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: Record<string, unknown>) => createSubscription(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      toast({ title: '項目已建立' })
      navigate('/subscriptions')
    },
    onError: () => {
      toast({ title: '建立失敗，請確認欄位後重試', variant: 'destructive' })
    },
  })

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">新增項目</h2>
      <SubscriptionForm onSubmit={mutate} isPending={isPending} submitLabel="建立" />
    </div>
  )
}
