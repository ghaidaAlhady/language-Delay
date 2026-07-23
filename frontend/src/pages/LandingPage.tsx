import { Link } from "react-router-dom";

import { Button } from "@/components/Button";
import { Card } from "@/components/Card";
import { Logo } from "@/components/Logo";
import { useAuth } from "@/features/auth/useAuth";

const DOMAIN_CARDS = [
  { title: "اللغة الاستقبالية", description: "فهم الطفل للكلام والتعليمات الموجهة إليه." },
  { title: "اللغة التعبيرية", description: "قدرة الطفل على التعبير عن نفسه بالكلمات والجمل." },
  { title: "التواصل والمهارات الاجتماعية", description: "التفاعل والتواصل غير اللفظي مع الآخرين." },
  { title: "النطق", description: "وضوح نطق الأصوات والكلمات." },
];

export function LandingPage() {
  const { status } = useAuth();
  const startHref = status === "authenticated" ? "/dashboard" : "/register";

  return (
    <div className="flex flex-col gap-16 px-4 py-12">
      <section className="mx-auto flex max-w-2xl flex-col items-center gap-6 text-center">
        <Logo className="h-16 w-16" />
        <div>
          <p className="text-sm font-medium text-primary-500">مدعوم بالمعرفة العلمية</p>
          <h1 className="mt-1 text-3xl font-bold text-primary-900 sm:text-4xl">
            المرشد الذكي للتأخر اللغوي لدى الأطفال
          </h1>
        </div>
        <p className="text-lg text-gray-600">
          تقييم أولي داعم لمهارات طفلك اللغوية، مع خطة أنشطة أسبوعية مخصصة لدعم نموه اللغوي.
        </p>
        <Link to={startHref}>
          <Button size="lg">ابدأ الآن</Button>
        </Link>
        <p className="text-sm text-gray-500">
          أداة داعمة لولي الأمر لتقييم أولي غير تشخيصي، وليست بديلاً عن أخصائي تخاطب مؤهل.
        </p>
      </section>

      <section className="mx-auto grid w-full max-w-4xl grid-cols-1 gap-4 sm:grid-cols-2">
        {DOMAIN_CARDS.map((card) => (
          <Card key={card.title}>
            <h2 className="font-semibold text-primary-900">{card.title}</h2>
            <p className="mt-1 text-sm text-gray-600">{card.description}</p>
          </Card>
        ))}
      </section>
    </div>
  );
}
