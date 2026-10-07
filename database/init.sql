CREATE TABLE IF NOT EXISTS settlement_records (
  id SERIAL PRIMARY KEY,
  settlement_no VARCHAR(64) UNIQUE NOT NULL,
  batch_no VARCHAR(64) NOT NULL,
  insured_id VARCHAR(32) NOT NULL,
  total_amount NUMERIC(12, 2) NOT NULL,
  reimbursable_base NUMERIC(12, 2) NOT NULL DEFAULT 0,
  reimbursed_amount NUMERIC(12, 2) NOT NULL,
  account_pay_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
  self_pay_amount NUMERIC(12, 2) NOT NULL,
  deductible NUMERIC(12, 2) NOT NULL DEFAULT 0,
  reimbursement_ratio NUMERIC(6, 4) NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 兼容已有库的表结构升级
ALTER TABLE settlement_records ADD COLUMN IF NOT EXISTS reimbursable_base NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE settlement_records ADD COLUMN IF NOT EXISTS account_pay_amount NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE settlement_records ADD COLUMN IF NOT EXISTS deductible NUMERIC(12, 2) NOT NULL DEFAULT 0;
ALTER TABLE settlement_records ADD COLUMN IF NOT EXISTS reimbursement_ratio NUMERIC(6, 4) NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  client_id VARCHAR(64) NOT NULL,
  path VARCHAR(255) NOT NULL,
  action VARCHAR(64) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
