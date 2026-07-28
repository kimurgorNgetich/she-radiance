-- SR-003: DIAGNOSTIC_LOG now records referral_flag instead of confidence_score.
ALTER TABLE diagnostic_log ADD COLUMN IF NOT EXISTS referral_flag BOOLEAN;
ALTER TABLE diagnostic_log ALTER COLUMN confidence_score DROP NOT NULL;
