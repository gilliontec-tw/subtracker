import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getSubscription, updateSubscription } from '@/api/subscriptions'
import { useToast } from '@/hooks/use-toast'
import SubscriptionForm, { toFormValues } from '@/components/subscriptions/SubscriptionForm'

export default function SubscriptionEditPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { toast } = useToast()

  const subId = parseInt(id ?? '', 10)

  const { data: subscription, isLoading, isError } = useQuery({
    queryKey: ['subscription', subId],
    queryFn: () => getSubscription(subId),
    enabled: Number.isInteger(subId) && subId > 0,
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (payload: Record<string, unknown>) => updateSubscription(subId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subscriptions'] })
      queryClient.invalidateQueries({ queryKey: ['subscription', subId] })
      toast({ title: '訂閱已更新' })
      navigate('/subscriptions')
    },
    onError: () => {
      toast({ title: '更新失敗，請確認欄位後重試', variant: 'destructive' })
    },
  })

  if (isLoading) return <p className="text-muted-foreground">載入中...</p>
  if (isError || !subscription) {
    return <p className="text-destructive">找不到此訂閱，請返回列表</p>
  }

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">編輯訂閱</h2>
      <SubscriptionForm
        defaultValues={toFormValues(subscription)}
        onSubmit={mutate}
        isPending={isPending}
        submitLabel="儲存"
        subscriptionId={subId}
        serviceName={subscription.service_name}
      />
    </div>
  )
}
