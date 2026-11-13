import http from './http'
import type { KeyConfig, ExceptionSummary, RuleException } from '../types/exception'
import type { Page } from '../types/api'

export interface ExceptionFilters {
  dataset_id?: number | null
  rule_id?: number | null
  status?: string | null
  page?: number
  page_size?: number
}

export async function fetchKeyConfig(datasetId: number): Promise<{ config: KeyConfig | null }> {
  const { data } = await http.get(`/datasets/${datasetId}/key-config`)
  return data
}

export async function saveKeyConfig(datasetId: number, keyColumns: string[]): Promise<{ config: KeyConfig }> {
  const { data } = await http.put(`/datasets/${datasetId}/key-config`, { key_columns: keyColumns })
  return data
}

export async function fetchExceptions(filters: ExceptionFilters = {}): Promise<Page<RuleException>> {
  const params: Record<string, unknown> = {}
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== null && value !== undefined && value !== '') params[key] = value
  })
  const { data } = await http.get<Page<RuleException>>('/exceptions', { params })
  return data
}

export async function fetchExceptionSummary(datasetId?: number | null): Promise<ExceptionSummary> {
  const { data } = await http.get<ExceptionSummary>('/exceptions/summary', {
    params: datasetId ? { dataset_id: datasetId } : {},
  })
  return data
}

export async function fetchException(exceptionId: number): Promise<RuleException> {
  const { data } = await http.get<RuleException>(`/exceptions/${exceptionId}`)
  return data
}

export interface RegisterExceptionPayload {
  rule_id: number
  row_index: number
  approval_basis: string
  approver: string
  expire_date: string | null
}

export async function registerException(payload: RegisterExceptionPayload): Promise<RuleException> {
  const { data } = await http.post<RuleException>('/exceptions', payload)
  return data
}

export async function revokeException(
  exceptionId: number,
  reason: string | null,
): Promise<RuleException> {
  const { data } = await http.post<RuleException>(`/exceptions/${exceptionId}/revoke`, { reason })
  return data
}
