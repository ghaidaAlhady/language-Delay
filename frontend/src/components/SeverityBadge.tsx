import type { Severity } from "@/types/api";

const SEVERITY_CLASSES: Record<Severity, string> = {
  طبيعي: "bg-success-50 text-success-600",
  "تأخر بسيط": "bg-warning-50 text-warning-600",
  "تأخر متوسط": "bg-warning-50 text-orange-700",
  "تأخر ملحوظ": "bg-danger-50 text-danger-600",
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-sm font-semibold ${SEVERITY_CLASSES[severity]}`}>
      {severity}
    </span>
  );
}
