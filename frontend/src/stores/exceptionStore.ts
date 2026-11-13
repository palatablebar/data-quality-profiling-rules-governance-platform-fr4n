import { defineStore } from 'pinia'
import {
  fetchException,
  fetchExceptions,
  fetchExceptionSummary,
  registerException,
  revokeException,
  type ExceptionFilters,
  type RegisterExceptionPayload,
} from '../api/exception'
import type { ExceptionSummary, RuleException } from '../types/exception'

interface ExceptionStoreState {
  items: RuleException[]
  total: number
  summary: ExceptionSummary | null
  filters: ExceptionFilters
  loading: boolean
  error: string
  selected: RuleException | null
}

export const useExceptionStore = defineStore('exception', {
  state: (): ExceptionStoreState => ({
    items: [],
    total: 0,
    summary: null,
    filters: { dataset_id: null, rule_id: null, status: null },
    loading: false,
    error: '',
    selected: null,
  }),
  actions: {
    async load() {
      this.loading = true
      this.error = ''
      try {
        const page = await fetchExceptions({ ...this.filters, page_size: 200 })
        this.items = page.items
        this.total = page.total
        this.summary = await fetchExceptionSummary(this.filters.dataset_id ?? null)
      } catch (error) {
        this.error = (error as { message?: string }).message ?? '例外台账加载失败'
      } finally {
        this.loading = false
      }
    },
    async refreshSummary(datasetId: number | null = null) {
      this.summary = await fetchExceptionSummary(datasetId)
    },
    async open(exceptionId: number) {
      this.selected = await fetchException(exceptionId)
      return this.selected
    },
    close() {
      this.selected = null
    },
    async register(payload: RegisterExceptionPayload) {
      const exc = await registerException(payload)
      await this.load()
      return exc
    },
    async revoke(exceptionId: number, reason: string | null) {
      const exc = await revokeException(exceptionId, reason)
      if (this.selected?.id === exceptionId) this.selected = exc
      await this.load()
      return exc
    },
  },
})
