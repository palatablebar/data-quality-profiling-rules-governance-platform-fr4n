<template>
  <Teleport to="body">
    <Transition name="drawer">
      <div v-if="open" class="fixed inset-0 z-40">
        <div class="absolute inset-0 bg-ink/20" @click="$emit('close')"></div>
        <aside class="absolute right-0 top-0 h-full w-[520px] max-w-full bg-paper border-l border-rule flex flex-col">
          <div class="px-6 pt-5 pb-3 border-b border-rule">
            <div class="eyebrow">register exception</div>
            <h2 class="display !text-[20px] mt-1">登记已批准例外</h2>
            <p class="mt-1 text-[11.5px] text-ink-soft">
              按「规则 + 业务主键」登记；同一主键重复扫描不会新增例外，业务字段变化后例外自动失效。
            </p>
          </div>

          <div class="flex-1 overflow-y-auto px-6 py-4">
            <dl class="grid grid-cols-2 gap-x-6 gap-y-3">
              <div class="col-span-2">
                <dt class="label">规则</dt>
                <dd class="text-[12.5px] mt-0.5">{{ issue.rule_name ?? `规则 #${issue.rule_id}` }}</dd>
              </div>
              <div>
                <dt class="label">row_index</dt>
                <dd class="text-[12.5px] tabular-nums mt-0.5">{{ issue.row_index }}</dd>
              </div>
              <div>
                <dt class="label">observed_value</dt>
                <dd class="text-[12px] tabular-nums mt-0.5 break-all">
                  {{ issue.observed_value === '' ? '（空）' : issue.observed_value }}
                </dd>
              </div>
              <div v-if="issue.business_key" class="col-span-2">
                <dt class="label">业务主键</dt>
                <dd class="text-[12.5px] tabular-nums mt-0.5 break-all">{{ issue.business_key }}</dd>
              </div>
            </dl>

            <div class="mt-5">
              <div class="label mb-1">审批依据 <span class="text-[var(--alert)]">*</span></div>
              <textarea
                v-model="form.approval_basis"
                class="input min-h-[84px]"
                placeholder="例如：审计例会 2026-10 批复，监管报送例外台账 EX-0143"
              ></textarea>
            </div>
            <div class="mt-4 grid grid-cols-2 gap-4">
              <div>
                <div class="label mb-1">审批人 <span class="text-[var(--alert)]">*</span></div>
                <input v-model="form.approver" class="input" placeholder="例如：顾清和" />
              </div>
              <div>
                <div class="label mb-1">截止日期</div>
                <input v-model="form.expire_date" type="date" class="input" />
                <div class="text-[10.5px] text-ink-soft mt-1">留空表示长期有效，到期自动恢复待办</div>
              </div>
            </div>

            <ErrorNotice :error="error" />
          </div>

          <div class="px-6 py-3 border-t border-rule flex justify-end gap-2">
            <button class="btn" @click="$emit('close')">取消</button>
            <button class="btn btn-solid" :disabled="submitting || !canSubmit" @click="submit">
              {{ submitting ? '提交中…' : '登记例外' }}
            </button>
          </div>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue'
import ErrorNotice from '../common/ErrorNotice.vue'
import { useExceptionStore } from '../../stores/exceptionStore'
import type { Issue } from '../../types/issue'

const props = defineProps<{ open: boolean; issue: Issue }>()
const emit = defineEmits<{ close: []; registered: [] }>()

const store = useExceptionStore()
const submitting = ref(false)
const error = ref('')
const form = reactive({
  approval_basis: '',
  approver: '',
  expire_date: '',
})

const canSubmit = computed(
  () => form.approval_basis.trim().length >= 2 && form.approver.trim().length >= 1,
)

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  error.value = ''
  try {
    await store.register({
      rule_id: props.issue.rule_id as number,
      row_index: props.issue.row_index,
      approval_basis: form.approval_basis.trim(),
      approver: form.approver.trim(),
      expire_date: form.expire_date || null,
    })
    form.approval_basis = ''
    form.approver = ''
    form.expire_date = ''
    emit('registered')
    emit('close')
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '登记失败'
  } finally {
    submitting.value = false
  }
}
</script>
