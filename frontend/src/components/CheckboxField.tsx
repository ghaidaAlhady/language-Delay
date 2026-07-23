import { forwardRef, useId, type InputHTMLAttributes } from "react";

export interface CheckboxFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
}

export const CheckboxField = forwardRef<HTMLInputElement, CheckboxFieldProps>(
  function CheckboxField({ label, id, className = "", ...rest }, ref) {
    const generatedId = useId();
    const fieldId = id ?? generatedId;

    return (
      <div className="flex items-center gap-2">
        <input
          ref={ref}
          type="checkbox"
          id={fieldId}
          className={`h-5 w-5 rounded border-primary-300 text-primary-500 focus-visible:outline-3 focus-visible:outline-primary-500 ${className}`}
          {...rest}
        />
        <label htmlFor={fieldId} className="text-sm text-primary-900">
          {label}
        </label>
      </div>
    );
  },
);
