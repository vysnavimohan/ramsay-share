-- Ramsay demo — Lakebase seed questions (starter prompts surfaced by the app).
-- Idempotent: recreate table + reload the 4 canonical questions.
CREATE TABLE IF NOT EXISTS seed_questions (
    ordinal    INT PRIMARY KEY,
    text       TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

TRUNCATE seed_questions;

INSERT INTO seed_questions (ordinal, text) VALUES
(1, 'If I close 2 theatres for 3 days at Springfield Hospital from 2026-09-14 to 2026-09-16, what are the implications? Which surgeries are impacted and can they be shifted elsewhere? What is the earliest date to do this with least disruption?'),
(2, 'If referrals keep growing at the current rate, which hospital hits theatre or bed capacity first over the next quarter, how many more staff would we need, and what happens to waiting times?'),
(3, 'How many patients over 55 referred for Trauma and Orthopaedics are on an admitted RTT pathway, by hospital?'),
(4, 'Which hospital has the lowest wait times? Compare to the ones with the highest wait times and tell me the root cause.');
