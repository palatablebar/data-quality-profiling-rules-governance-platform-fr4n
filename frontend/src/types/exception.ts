export interface ExceptionHit {
  id: number
  exception_id: number
  run_id: number
  report_no: string | null
  rule_id: number
  row_index: number
  business_key: string
  observed_value: string | null
  suppressed: boolean
  exception_status: string
  detail: string | null
  issue_id: number | null
  created_at: string | null
}

export interface RuleException {
  id: number
  rule_id: number
  rule_name: string | null
  rule_type: string | null
  severity: string
  column_name: string | null
  dataset_id: number
  dataset_name: string | null
  business_key: string
  key_columns: string[]
  snapshot: Record<string, string>
  approval_basis: string
  approver: string
  expire_date: string | null
  status: string
  close_reason: string | null
  created_by: number
  creator_name: string | null
  created_at: string | null
  updated_at: string | null
  closed_at: string | null
  hits?: ExceptionHit[]
}

export interface ExceptionSummary {
  dataset_id: number | null
  suppressed: number
  resumed: number
  pending: number
  by_status: Record<string, number>
  total: number
}

export interface KeyConfig {
  id: number
  dataset_id: number
  key_columns: string[]
  created_by: number
  created_at: string | null
  updated_at: string | null
}
