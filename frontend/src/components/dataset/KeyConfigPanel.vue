<template>
  <section class="mt-8 border-t border-rule pt-4">
    <div class="flex items-center justify-between">
      <div>
        <div class="eyebrow">业务主键（例外登记基准）</div>
        <p class="text-[11.5px] text-ink-soft mt-1">
          例外按「规则 + 主键值」识别，数据重排不影响；最多 8 列，主键列不允许有空值。
        </p>
      </div>
      <button v-if="auth.canWrite" class="btn !py-1" @click="editing = !editing">
        {{ editing ? '收起' : config?.key_columns.length ? '修改主键' : '指定主键' }}
      </button>
    </div>

    <div class="mt-3">
      <div v-if="config?.key_columns.length" class="flex flex-wrap gap-2">
        <span
          v-for="column in config.key_columns"
          :key="column"
          class="stamp"
          style="color: var(--assay)"
        >
          {{ column }}
        </span>
        <span class="text-[10.5px] text-ink-soft self-center">
          由用户 #{{ config.created_by }} 配置 · 更新于 {{ config.updated_at ?? config.created_at }}
        </span>
      </div>
      <div v-else class="text-[12px] text-ink-soft border border-dashed border-rule px-3 py-3">
        尚未指定业务主键——在问题分诊板登记例外前需要先配置。
      </div>
    </div>

    <div v-if="editing" class="mt-4 border border-rule bg-paper-2 px-4 py-3">
      <div class="label mb-2">选择组成主键的列（顺序即组合顺序）</div>
      <div class="flex flex-wrap gap-x-5 gap-y-2 max-h-[180px] overflow-y-auto">
        <label
          v-for="column in columns"
          :key="column.column_name"
          class="flex items-center gap-2 text-[12px] cursor-pointer"
        >
          <input
            type="checkbox"
            :value="column.column_name"
            :checked="draft.includes(column.column_name)"
            @change="toggle(column.column_name)"
          />
          <span class="tabular-nums">{{ column.column_name }}</span>
          <span class="text-[10px] text-ink-soft">{{ column.type_label }}</span>
        </label>
      </div>
      <ErrorNotice :error="error" />
      <div class="mt-3 flex items-center gap-2">
        <button class="btn btn-solid !py-1" :disabled="saving || !draft.length" @click="save">
          {{ saving ? '保存中…' : '保存主键配置' }}
        </button>
        <button class="btn !py-1" @click="cancel">取消</button>
        <span v-if="changed && draft.length" class="text-[10.5px]" style="color: var(--alert-deep)">
          修改主键将使该数据集现有有效例外全部失效
        </span>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ErrorNotice from '../common/ErrorNotice.vue'
import { fetchColumns } from '../../api/profile'
import { fetchKeyConfig, saveKeyConfig } from '../../api/exception'
import { useAuthStore } from '../../stores/authStore'
import type { KeyConfig } from '../../types/exception'
import type { ColumnProfile } from '../../types/profile'

const props = defineProps<{ datasetId: number }>()
const emit = defineEmits<{ saved: [] }>()

const auth = useAuthStore()
const config = ref<KeyConfig | null>(null)
const columns = ref<ColumnProfile[]>([])
const draft = ref<string[]>([])
const editing = ref(false)
const saving = ref(false)
const error = ref('')

const changed = computed(
  () => config.value?.key_columns.join('|') !== draft.value.join('|'),
)

onMounted(load)

async function load() {
  const [keyResult, columnResult] = await Promise.all([
    fetchKeyConfig(props.datasetId),
    fetchColumns(props.datasetId),
  ])
  config.value = keyResult.config
  columns.value = columnResult.columns
  draft.value = keyResult.config ? [...keyResult.config.key_columns] : []
}

function toggle(columnName: string) {
  const index = draft.value.indexOf(columnName)
  if (index >= 0) draft.value.splice(index, 1)
  else if (draft.value.length < 8) draft.value.push(columnName)
}

function cancel() {
  editing.value = false
  error.value = ''
  draft.value = config.value ? [...config.value.key_columns] : []
}

async function save() {
  if (!draft.value.length) return
  saving.value = true
  error.value = ''
  try {
    const result = await saveKeyConfig(props.datasetId, draft.value)
    config.value = result.config
    editing.value = false
    emit('saved')
  } catch (err) {
    error.value = (err as { message?: string }).message ?? '主键配置保存失败'
  } finally {
    saving.value = false
  }
}
</script>
