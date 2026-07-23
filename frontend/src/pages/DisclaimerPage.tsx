import { StaticContentPage } from "@/components/StaticContentPage";

export function DisclaimerPage() {
  return (
    <StaticContentPage title="إخلاء المسؤولية المهني والطبي">
      <p className="rounded-card bg-warning-50 p-4 font-medium text-primary-900">
        هذا التطبيق أداة دعم لولي الأمر، وليس أداة تشخيص طبي.
      </p>
      <p>
        نتائج التقييم والتقارير والتوصيات المقدمة في هذا التطبيق هي تقييم أولي داعم مبني على
        إجابات ولي الأمر، ولا تُعد تشخيصًا طبيًا أو نفسيًا بأي شكل من الأشكال.
      </p>
      <p>
        لا يغني استخدام هذا التطبيق عن استشارة أخصائي تخاطب أو أي أخصائي رعاية صحية مؤهل. إذا
        أشارت النتائج إلى وجود مؤشرات تستدعي القلق، يوصي التطبيق بمراجعة أخصائي تخاطب لتقييم
        دقيق ومتابعة مناسبة.
      </p>
    </StaticContentPage>
  );
}
