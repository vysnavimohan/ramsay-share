CREATE VIEW ramsay_health.ops.mv_patient_activity (
  Site,
  Service,
  Payor,
  Urgency,
  Referral Date,
  Referrals,
  Patients,
  Admissions,
  Avg Wait Weeks,
  Avg Wait Days)
COMMENT 'Patient activity: referrals, admissions, waits by site/service/payor'
WITH METRICS
LANGUAGE YAML
AS
$$
version: 1.1

source: ramsay_health.ops.vw_referral_flow

comment: "Patient activity: referrals, admissions, waits by site/service/payor"

dimensions:
  - name: Site
    expr: SiteName

  - name: Service
    expr: ServiceName

  - name: Payor
    expr: PayorType

  - name: Urgency
    expr: ReferralUrgency

  - name: Referral Date
    expr: CAST(ReferralRaisedTS AS DATE)

measures:
  - name: Referrals
    expr: COUNT(DISTINCT ReferralID)

  - name: Patients
    expr: COUNT(DISTINCT PatientKey)

  - name: Admissions
    expr: SUM(HasAdmission)

  - name: Avg Wait Weeks
    expr: AVG(WeeksWaiting)

  - name: Avg Wait Days
    expr: AVG(CurrentWaitDays)
$$
;
