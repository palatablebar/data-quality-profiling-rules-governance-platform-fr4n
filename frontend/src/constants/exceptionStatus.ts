// ExceptionStatus — mirror of backend/app/constants/exception_status.py
export enum ExceptionStatus {
  ACTIVE = 'active',
  EXPIRED = 'expired',
  INVALIDATED = 'invalidated',
  REVOKED = 'revoked',
}

export const EXCEPTION_STATUS_LABELS: Record<string, string> = {
  [ExceptionStatus.ACTIVE]: '有效（暂缓中）',
  [ExceptionStatus.EXPIRED]: '已到期',
  [ExceptionStatus.INVALIDATED]: '已失效（字段变更）',
  [ExceptionStatus.REVOKED]: '已撤销',
}

export const EXCEPTION_STATUS_LIST = [
  ExceptionStatus.ACTIVE,
  ExceptionStatus.EXPIRED,
  ExceptionStatus.INVALIDATED,
  ExceptionStatus.REVOKED,
]

// badge tones reuse the lab-report palette: active=assay blue, lapsed=alert orange
export const EXCEPTION_STATUS_TONE: Record<string, string> = {
  [ExceptionStatus.ACTIVE]: 'var(--assay)',
  [ExceptionStatus.EXPIRED]: 'var(--alert)',
  [ExceptionStatus.INVALIDATED]: 'var(--alert-deep)',
  [ExceptionStatus.REVOKED]: 'var(--ink-soft)',
}
