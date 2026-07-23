/** Centralized TanStack Query key factory — one place to keep cache keys in sync. */
export const queryKeys = {
  me: ["me"] as const,
  children: {
    all: ["children"] as const,
    detail: (childId: string) => ["children", childId] as const,
  },
  assessments: {
    forChild: (childId: string) => ["assessments", "byChild", childId] as const,
    detail: (assessmentId: string) => ["assessments", assessmentId] as const,
    questions: (assessmentId: string) => ["assessments", assessmentId, "questions"] as const,
    activities: (assessmentId: string) => ["assessments", assessmentId, "activities"] as const,
  },
  reports: {
    forChild: (childId: string) => ["reports", "byChild", childId] as const,
    detail: (reportId: string) => ["reports", reportId] as const,
  },
  weeklyPlan: {
    active: (childId: string) => ["weeklyPlan", childId] as const,
  },
  followups: {
    forChild: (childId: string) => ["followups", "byChild", childId] as const,
    detail: (followupId: string) => ["followups", followupId] as const,
  },
} as const;
