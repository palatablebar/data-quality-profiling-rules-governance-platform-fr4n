<template>
  <div class="paper-page">
    <PageHeader
      eyebrow="exception ledger"
      title="例外审批台账"
      subtitle="按规则与业务主键登记已批准例外：扫描照实记录，命中有效例外的问题暂缓进待办，到期或字段变化自动恢复。"
      :meta="meta"
    />

    <div class="grid grid-cols-3 gap-4 mt-2 mb-5">
      <div class="border border-rule bg-paper-2 px-5 py-4">
        <div class="label">暂缓（有效例外）</div>
        <div class="text-[28px] tabular-nums mt-1" style="color: var(--assay)">
          {{ store.summary?.suppressed ?? 0 }}
        </div>
        <div class="text-[10.5px] text-ink-soft mt-1">命中的问题不进待办，扫描历史仍逐条留存</div>
      </div>
      <div class="border border-rule bg-paper-2 px-5 py-4">
        <div class="label">到期恢复</div>
        <div class="text-[28px] tabular-nums mt-1" style="color: var(--alert)">
          {{ store.summary?.resumed ?? 0 }}
        </div>
        <div class="text-[10.5px] text-ink-soft mt-1">例外失效后重新进入待办的问题数</div>
      </div>
      <div class="border border-rule bg-paper-2 px-5 py-4">
        <div class="label">待处理问题</div>
        <div class="text-[28px] tabular-nums mt-1">{{ store.summary?.pending ?? 0 }}</div>
        <div class="text-[10.5px] text-ink-soft mt-1">分诊板上 open / 已指派 的全部问题</div>
      </div>
    </div>

    <div class="flex flex-wrap items-end gap-4 py-3 border-b border-rule">
      <div>
        <div class="label mb-1">数据集</div>
        <select v-model="store.filters.dataset_id" class="input !w-[210px]" @change="store.load()">
          <option :value="null">全部数据集</option>
          <option v-for="dataset in datasetStore.items" :key="dataset.id" :value="dataset.id">
            {{ dataset.name }}
          </option>
        </select>
      </div>
      <div>
        <div class="label mb-1">状态</div>
        <select v-model="store.filters.status" class="input !w-[160px]" @change="store.load()">
          <option :value="null">全部状态</option>
          <option v-for="status in EXCEPTION_STATUS_LIST" :key="status" :value="status">
            {{ EXCEPTION_STATUS_LABELS[status] }}
          </option>
        </select>
      </div>
      <button class="btn" @click="reset">重置筛选</button>
      <span class="text-[11px] text-ink-soft ml-auto tabular-nums">共 {{ store.total }} 条例外</span>
    </div>

    <ErrorNotice :error="store.error" />

    <table v-if="store.items.length" class="table-base mt-2">
      <thead>
        <tr>
          <th class="w-[96px]">状态</th>
          <th>规则 / 列</th>
          <th>业务主键</th>
          <th class="w-[150px]">审批依据</th>
          <th class="w-[90px]">审批人</th>
          <th class="w-[104px]">截止日期</th>
          <th class="w-[86px]"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="exc in store.items" :key="exc.id" class="cursor-pointer" @click="openDetail(exc.id)">
          <td><ExceptionStatusBadge :status="exc.status" /></td>
          <td>
            <div class="text-[12px]">{{ exc.rule_name ?? '-' }}</div>
            <div class="text-[10.5px] text-ink-soft">{{ exc.column_name }} · {{ exc.dataset_name }}</div>
          </td>
          <td class="text-[11.5px] tabular-nums break-all">{{ exc.business_key }}</td>
          <td class="text-[11px] text-ink-soft break-all line-clamp-2">{{ exc.approval_basis }}</td>
          <td class="text-[11.5px]">{{ exc.approver }}</td>
          <td class="text-[11.5px] tabular-nums">{{ exc.expire_date ?? '长期' }}</td>
          <td class="text-right">
            <button class="link-button text-[11px]" @click.stop="openDetail(exc.id)">明细 / 命中 →</button>
          </td>
        </tr>
      </tbody>
    </table>

    <EmptyState
      v-else-if="!store.loading"
      class="mt-6"
      title="还没有登记例外"
      description="在问题分诊板打开一条问题，填写审批依据与截止日期即可登记；需要先为数据集指定业务主键。"
    >
      <RouterLink to="/issues" class="btn">去问题分诊板</RouterLink>
    </EmptyState>

    <ExceptionDrawer :exception="store.selected" @close="store.close()" />
    <ActivityTrail />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import PageHeader from '../components/common/PageHeader.vue'
import EmptyState from '../components/common/EmptyState.vue'
import ErrorNotice from '../components/common/ErrorNotice.vue'
import ActivityTrail from '../components/common/ActivityTrail.vue'
import ExceptionStatusBadge from '../components/exception/ExceptionStatusBadge.vue'
import ExceptionDrawer from '../components/exception/ExceptionDrawer.vue'
import { useExceptionStore } from '../stores/exceptionStore'
import { useDatasetStore } from '../stores/datasetStore'
import { EXCEPTION_STATUS_LABELS, EXCEPTION_STATUS_LIST } from '../constants/exceptionStatus'

const route = useRoute()
const store = useExceptionStore()
const datasetStore = useDatasetStore()

const meta = computed(() => [
  { label: '例外总数', value: String(store.summary?.total ?? store.total) },
  { label: '暂缓', value: String(store.summary?.suppressed ?? 0) },
  { label: '到期恢复', value: String(store.summary?.resumed ?? 0) },
  { label: '待处理', value: String(store.summary?.pending ?? 0) },
])

function reset() {
  store.filters = { dataset_id: null, rule_id: null, status: null }
  store.load()
}

async function openDetail(exceptionId: number) {
  await store.open(exceptionId)
}

onMounted(async () => {
  if (!datasetStore.items.length) await datasetStore.load()
  if (route.query.dataset) store.filters.dataset_id = Number(route.query.dataset)
  if (route.query.status) store.filters.status = String(route.query.status)
  await store.load()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
