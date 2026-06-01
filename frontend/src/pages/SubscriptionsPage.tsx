import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { listSubscriptions } from '@/api/subscriptions'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import SubscriptionTable from '@/components/subscriptions/SubscriptionTable'
import { useAuthStore } from '@/stores/authStore'
import { Plus } from 'lucide-react'

export default function SubscriptionsPage() {
  const navigate = useNavigate()
  const { currentUser } = useAuthStore()
  const [search, setSearch] = useState('')
  const [showCancelled, setShowCancelled] = useState(false)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['subscriptions', showCancelled],
    queryFn: () => listSubscriptions(showCancelled),
  })

  const subscriptions = data?.items ?? []
  const filtered = subscriptions.filter((s) =>
    s.service_name.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">訂閱管理</h2>
        {currentUser?.can_create && (
          <Button onClick={() => navigate('/subscriptions/new')}>
            <Plus className="size-4" />
            新增訂閱
          </Button>
        )}
      </div>

      <div className="flex items-center gap-4">
        <Input
          placeholder="搜尋服務名稱..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-sm"
        />
        <label className="flex cursor-pointer items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={showCancelled}
            onChange={(e) => setShowCancelled(e.target.checked)}
            className="size-4"
          />
          顯示已取消
        </label>
      </div>

      {isLoading && <p className="text-muted-foreground">載入中...</p>}
      {isError && <p className="text-destructive">載入失敗，請重新整理頁面</p>}
      {!isLoading && !isError && <SubscriptionTable subscriptions={filtered} />}
    </div>
  )
}
