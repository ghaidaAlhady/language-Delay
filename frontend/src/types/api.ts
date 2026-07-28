/**
 * Hand-mapped TypeScript types mirroring the real FastAPI backend contracts
 * (`backend/app/schemas/*.py`, `backend/app/rag/schemas.py`), cross-checked
 * against the live `/openapi.json`. These are the wire types — every field
 * name and enum value here must match the backend exactly.
 */

export const DOMAINS = [
  "اللغة الاستقبالية",
  "اللغة التعبيرية",
  "التواصل والمهارات الاجتماعية",
  "النطق",
] as const;
export type Domain = (typeof DOMAINS)[number];

export const SEVERITIES = ["طبيعي", "تأخر بسيط", "تأخر متوسط", "تأخر ملحوظ"] as const;
export type Severity = (typeof SEVERITIES)[number];

export const REFERRAL_GUIDANCE = ["لا", "يُنظر في الإحالة", "نعم"] as const;
export type ReferralGuidance = (typeof REFERRAL_GUIDANCE)[number];

export type Gender = "male" | "female";

export type AssessmentStatus = "in_progress" | "completed";

export const RESPONSE_VALUES = ["always", "often", "sometimes", "rarely", "never"] as const;
export type ResponseValue = (typeof RESPONSE_VALUES)[number];

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

// ---- Auth -------------------------------------------------------------

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

// ---- Children -----------------------------------------------------------

export interface ChildCreateRequest {
  name: string;
  date_of_birth: string;
  gender: Gender;
  home_language: string;
  has_previous_diagnosis: boolean;
  previous_diagnosis_details?: string | null;
  has_hearing_problems: boolean;
  uses_hearing_aid: boolean;
  notes?: string | null;
}

export type ChildUpdateRequest = Partial<ChildCreateRequest>;

export interface ChildResponse {
  id: string;
  name: string;
  date_of_birth: string;
  gender: Gender;
  home_language: string;
  has_previous_diagnosis: boolean;
  previous_diagnosis_details: string | null;
  has_hearing_problems: boolean;
  uses_hearing_aid: boolean;
  notes: string | null;
  age_years: number;
  is_assessment_age_eligible: boolean;
  created_at: string;
  updated_at: string;
}

// ---- Knowledge base (KB01/KB02) ------------------------------------------

export interface ActivityRecord {
  source_file: string;
  source_sheet: string;
  id: string;
  name: string;
  age: number;
  domain: Domain;
  target_skill: string;
  goal: string;
  description: string;
  tools: string;
  duration: string;
  frequency: string;
  difficulty: string;
  parent_instructions: string;
  expected_outcome: string;
  reference: string;
}

export interface ReferenceRecord {
  source_file: string;
  source_sheet: string;
  code: string;
  description: string;
}

// ---- Assessments ----------------------------------------------------------

export interface AssessmentQuestionResponse {
  id: string;
  age: number;
  domain: Domain;
  question: string;
  linked_milestone_id: string;
}

export interface AnswerItem {
  question_id: string;
  response: ResponseValue;
}

export interface AnswerSubmissionRequest {
  answers: AnswerItem[];
}

export interface AssessmentDomainResultResponse {
  domain: Domain;
  score_percent: number;
  severity: Severity;
  referral: ReferralGuidance;
  decision_rule_id: string;
  recommendation: string;
  follow_up: string;
  suggested_activity_ids: string[];
}

export interface AssessmentResponse {
  id: string;
  child_id: string;
  age_at_assessment: number;
  status: AssessmentStatus;
  started_at: string;
  completed_at: string | null;
  answered_count: number;
  total_questions: number;
  overall_severity: Severity | null;
  overall_referral: ReferralGuidance | null;
  confidence_score: number | null;
  priority_domains: Domain[];
  strengths: string[];
  support_needs: string[];
  domain_results: AssessmentDomainResultResponse[];
}

// ---- Reports --------------------------------------------------------------

export interface ReportDomainSummary {
  domain: Domain;
  score_percent: number;
  severity: Severity;
  recommendation: string;
}

export interface ReportResponse {
  id: string;
  report_number: string;
  language: string;
  child_id: string;
  child_name: string;
  child_age_years: number;
  assessment_id: string;
  generated_at: string;
  overall_severity: Severity;
  overall_referral: ReferralGuidance;
  referral_recommended: boolean;
  confidence_score: number;
  domain_summaries: ReportDomainSummary[];
  strengths: string[];
  support_needs: string[];
  summary_text: string;
  weekly_goal: string;
  recommended_activity_ids: string[];
  next_reassessment: string;
  disclaimer: string;
}

// ---- Weekly plan ------------------------------------------------------------

export interface WeeklyPlanActivityResponse {
  id: string;
  day: string;
  slot_order: number;
  completed: boolean;
  completed_at: string | null;
  activity: ActivityRecord;
}

export interface WeeklyPlanResponse {
  id: string;
  child_id: string;
  assessment_id: string;
  is_active: boolean;
  generated_at: string;
  total_activities: number;
  completed_count: number;
  adherence_percent: number;
  activities: WeeklyPlanActivityResponse[];
}

export interface ActivityCompletionRequest {
  completed: boolean;
}

// ---- Follow-up / reassessment -------------------------------------------------

export interface WeeklyFollowupQuestionResponse {
  id: string;
  source_question_id: string;
  source_file: string;
  weekly_plan_id: string;
  age: number;
  domain: Domain;
  weekly_goal: string;
  skill: string;
  activity_id: string;
  activity_name: string;
  expected_behavior: string;
  question: string;
  response_type: string;
  required: boolean;
  progress_weight: number;
  fallback_used: boolean;
}

export interface WeeklyFollowupContextResponse {
  child_id: string;
  child_name: string;
  weekly_plan_id: string;
  assessment_id: string;
  generated_at: string;
  completed_count: number;
  total_activities: number;
  weekly_goals: string[];
  questions: WeeklyFollowupQuestionResponse[];
}

export interface WeeklyFollowupSubmissionRequest {
  answers: AnswerItem[];
}

export interface FollowupResponse {
  id: string;
  child_id: string;
  previous_assessment_id: string;
  current_assessment_id: string | null;
  weekly_plan_id: string | null;
  previous_score_percent: number;
  current_score_percent: number;
  improvement_percent: number;
  improved_domains: Domain[];
  support_needed_domains: Domain[];
  comment: string;
  next_goal: string;
  created_at: string;
}
