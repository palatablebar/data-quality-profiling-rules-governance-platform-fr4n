<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="exception" class="fixed inset-0 z-40">
        <div class="absolute inset-0 bg-ink/20" @click="$emit('close')"></div>
        <aside class="absolute right-0 top-0 h-full w-[560px] max-w-full bg-paper border-l border-rule flex flex-col">
          <div class="px-6 pt-5 pb-3 border-b border-rule flex items-start justify-between gap-4">
            <div class="min-w-0">
              <div class="eyebrow">exception no. {{ exception.id }}</div>
              <h2 class="display !text-[19px] mt-1 break-all">{{ exception.business_key }}</h2>
              <div class="mt-2 flex items-center gap-3">
                <ExceptionStatusBadge :status="exception.status" />
                <span class="text-[11px] text-ink-soft">{{ exception.rule_name }} · {{ exception.dataset_name }}</span>
              </div>
            </div>
            <button class="btn !px-2 !py-1" @click="$emit('close')">关闭</button>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-4">
            <dl class="grid grid-cols-2 gap-x-6 gap-y-3">
              <div>
                <dt class="label">审批人</dt>
                <dd class="text-[12.5px] mt-0.5">{{ exception.approver }}</dd>
              </div>
              <div>
                <dt class="label">截止日期</dt>
                <dd class="text-[12.5px] tabular-nums mt-0.5">{{ exception.expire_date ?? '长期有效' }}</dd>
              </div>
              <div>
                <dt class="label">登记人</dt>
                <dd class="text-[12.5px] mt-0.5">{{ exception.creator_name ?? `用户 #${exception.created_by}` }}</dd>
              </div>
              <div>
                <dt class="label">登记时间</dt>
                <dd class="text-[12.5px] tabular-nums mt-0.5">{{ exception.created_at }}</dd>
              </div>
              <div class="col-span-2">
                <dt class="label">审批依据</dt>
                <dd class="text-[12.5px] mt-0.5 whitespace-pre-wrap break-all border border-rule bg-paper-2 px-3 py-2">
                  {{ exception.approval_basis }}
                </dd>
              </div>
              <div v-if="exception.close_reason" class="col-span-2">
                <dt class="label">结束原因</dt>
                <dd class="text-[12px] mt-0.5 text-[var(--alert-deep)]">{{ exception.close_reason }}</dd>
              </div>
            </dl>

            <div class="mt-5">
              <div class="label mb-1">登记时业务字段快照</div>
              <table class="table-base">
                <tbody>
                  <tr v-for="(value, column) in exception.snapshot" :key="column">
                    <td class="w-[150px] text-[11px] text-ink-soft align-top">{{ column }}</td>
                    <td class="text-[11.5px] tabular-nums break-all">{{ value === '' ? '（空）' : value }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div class="mt-6">
              <div class="label mb-2">历史命中（{{ exception.hits?.length ?? 0 }}）</div>
              <table v-if="exception.hits && exception.hits.length" class="table-base">
                <thead>
                  <tr>
                    <th>批次</th>
                    <th class="w-[70px] text-right">row_index</th>
                    <th class="w-[88px]">处理</th>
                    <th>说明</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="hit in exception.hits" :key="hit.id">
                    <td class="text-[11px]">{{ hit.report_no ?? `#${hit.run_id}` }}</td>
                    <td class="num text-[11.5px]">{{ hit.row_index }}</td>
                    <td>
                      <span
                        class="stamp"
                        :style="{ color: hit.suppressed ? 'var(--assay)' : 'var(--alert)' }"
                      >
                        {{ hit.suppressed ? '暂缓' : '恢复待办' }}
                      </span>
                    </td>
                    <td class="text-[11px] text-ink-soft">{{ hit.detail ?? '-' }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="text-[11.5px] text-ink-soft border border-dashed border-rule px-3 py-4 text-center">
                登记后尚未被扫描命中
              </div>
            </div>
          </div>

          <div v-if="canWrite && exception.status === 'active'" class="px-6 py-3 border-t border-rule flex justify-end">
            <button class="btn" :disabled="revoking" @click="confirmOpen = true">
              {{ revoking ? '处理中…' : '撤销例外' }}
            </button>
          </div>
        </aside>
      </div>
    </Transition>

    <ConfirmDialog
      :open="confirmOpen"
      title="撤销例外"
      message="撤销后下一次扫描命中该主键将重新生成待办问题，确认撤销？"
      @cancel="confirmOpen = false"
      @confirm="doRevoke"
    />
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ExceptionStatusBadge from './ExceptionStatusBadge.vue'
import ConfirmDialog from '../common/ConfirmDialog.vue'
import { useAuthStore } from '../../stores/authStore'
import { useExceptionStore } from '../../stores/exceptionStore'
import type { RuleException } from '../../types/exception'

const props = defineProps<{ exception: RuleException | null }>()
defineEmits<{ close: [] }>()

const auth = useAuthStore()
const store = useExceptionStore()
const canWrite = auth.canWrite
const confirmOpen = ref(false)
const revoking = ref(false)

async function doRevoke() {
  if (!props.exception) return
  confirmOpen.value = false
  revoking.value = true
  try {
    await store.revoke(props.exception.id, '人工撤销审批')
  } finally {
    revoking.value = false
  }
}
</script>
