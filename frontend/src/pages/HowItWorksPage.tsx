import { StaticContentPage } from "@/components/StaticContentPage";

const STEPS = [
  { title: "إنشاء ملف الطفل", description: "أدخل بيانات طفلك الأساسية مثل الاسم وتاريخ الميلاد." },
  { title: "التقييم الأولي", description: "أجب عن مجموعة أسئلة مناسبة لعمر الطفل، سؤالًا واحدًا في كل مرة." },
  { title: "النتيجة والتقرير", description: "احصل على ملخص لنقاط القوة والمهارات التي تحتاج دعمًا، وتقرير عربي قابل للتنزيل." },
  { title: "الخطة الأسبوعية", description: "خطة من سبعة أيام بنشاطين يوميًا مبنية على نتائج التقييم." },
  { title: "المتابعة الأسبوعية", description: "بعد أسبوع من تنفيذ الخطة، أعد التقييم لمتابعة التقدم والحصول على خطة محدثة." },
];

export function HowItWorksPage() {
  return (
    <StaticContentPage title="كيف يعمل النظام">
      <ol className="flex flex-col gap-4">
        {STEPS.map((step, index) => (
          <li key={step.title} className="flex gap-3">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold text-white">
              {index + 1}
            </span>
            <div>
              <p className="font-semibold text-primary-900">{step.title}</p>
              <p className="text-sm text-gray-600">{step.description}</p>
            </div>
          </li>
        ))}
      </ol>
    </StaticContentPage>
  );
}
