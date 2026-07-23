export const WEEK_DAYS_ORDER = [
  "الأحد",
  "الاثنين",
  "الثلاثاء",
  "الأربعاء",
  "الخميس",
  "الجمعة",
  "السبت",
] as const;

export function dayIndex(day: string): number {
  const index = WEEK_DAYS_ORDER.indexOf(day as (typeof WEEK_DAYS_ORDER)[number]);
  return index === -1 ? WEEK_DAYS_ORDER.length : index;
}
