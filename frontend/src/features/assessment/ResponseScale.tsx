import type { ResponseValue } from "@/types/api";

const OPTIONS: { value: ResponseValue; label: string }[] = [
  { value: "always", label: "دائمًا" },
  { value: "often", label: "غالبًا" },
  { value: "sometimes", label: "أحيانًا" },
  { value: "rarely", label: "نادرًا" },
  { value: "never", label: "أبدًا" },
];

interface ResponseScaleProps {
  value: ResponseValue | null;
  onChange: (value: ResponseValue) => void;
  disabled?: boolean;
}

export function ResponseScale({ value, onChange, disabled = false }: ResponseScaleProps) {
  return (
    <div role="radiogroup" aria-label="درجة الاستجابة" className="grid grid-cols-1 gap-2 sm:grid-cols-5">
      {OPTIONS.map((option) => {
        const selected = value === option.value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={selected}
            disabled={disabled}
            onClick={() => onChange(option.value)}
            className={`rounded-xl border-2 px-4 py-3 text-sm font-medium transition-colors focus-visible:outline-3 focus-visible:outline-primary-500 disabled:cursor-not-allowed disabled:opacity-60 ${
              selected
                ? "border-primary-500 bg-primary-500 text-white"
                : "border-primary-200 bg-white text-primary-900 hover:border-primary-400"
            }`}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
