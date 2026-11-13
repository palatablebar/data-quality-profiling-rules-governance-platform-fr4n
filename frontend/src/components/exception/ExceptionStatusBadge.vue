<template>
  <span class="stamp" :style="{ color: tone }">{{ EXCEPTION_STATUS_LABELS[status] ?? status }}</span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { EXCEPTION_STATUS_LABELS, EXCEPTION_STATUS_TONE } from '../../constants/exceptionStatus'

const props = defineProps<{ status: string }>()
const tone = computed(() => EXCEPTION_STATUS_TONE[props.status] ?? 'var(--ink-soft)')
</script>
