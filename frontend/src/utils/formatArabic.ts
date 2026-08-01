const DATE_FORMATTER = new Intl.DateTimeFormat("ar-SA", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

const NUMBER_FORMATTER = new Intl.NumberFormat("ar-SA");

const PERCENT_FORMATTER = new Intl.NumberFormat("ar-SA", { maximumFractionDigits: 0 });

export function formatArabicDate(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return isoDate;
  return DATE_FORMATTER.format(date);
}

export function formatArabicNumber(value: number): string {
  return NUMBER_FORMATTER.format(value);
}

export function formatArabicPercent(value: number): string {
  return `${PERCENT_FORMATTER.format(value)}%`;
}

const AGE_UNIT = (age: number): string => {
  if (age === 1) return "سنة واحدة";
  if (age === 2) return "سنتان";
  if (age >= 3 && age <= 10) return `${formatArabicNumber(age)} سنوات`;
  return `${formatArabicNumber(age)} سنة`;
};

export function formatChildAge(ageYears: number): string {
  return AGE_UNIT(ageYears);
}
