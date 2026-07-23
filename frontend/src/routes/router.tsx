import { createBrowserRouter, RouterProvider } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { PublicLayout } from "@/layouts/PublicLayout";
import { AboutPage } from "@/pages/AboutPage";
import { AddChildPage } from "@/pages/AddChildPage";
import { AssessmentHistoryPage } from "@/pages/AssessmentHistoryPage";
import { AssessmentIntroPage } from "@/pages/AssessmentIntroPage";
import { AssessmentResultPage } from "@/pages/AssessmentResultPage";
import { AssessmentTakePage } from "@/pages/AssessmentTakePage";
import { ChildDetailPage } from "@/pages/ChildDetailPage";
import { ChildrenListPage } from "@/pages/ChildrenListPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DisclaimerPage } from "@/pages/DisclaimerPage";
import { EditChildPage } from "@/pages/EditChildPage";
import { ErrorPage } from "@/pages/ErrorPage";
import { FollowupDetailPage } from "@/pages/FollowupDetailPage";
import { HowItWorksPage } from "@/pages/HowItWorksPage";
import { LandingPage } from "@/pages/LandingPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { PrivacyPage } from "@/pages/PrivacyPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { ReassessmentPage } from "@/pages/ReassessmentPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ReportHistoryPage } from "@/pages/ReportHistoryPage";
import { ReportPage } from "@/pages/ReportPage";
import { WeeklyPlanPage } from "@/pages/WeeklyPlanPage";
import { ProtectedRoute } from "@/routes/ProtectedRoute";

const router = createBrowserRouter([
  {
    element: <PublicLayout />,
    errorElement: <ErrorPage />,
    children: [
      { path: "/", element: <LandingPage /> },
      { path: "/about", element: <AboutPage /> },
      { path: "/how-it-works", element: <HowItWorksPage /> },
      { path: "/privacy", element: <PrivacyPage /> },
      { path: "/disclaimer", element: <DisclaimerPage /> },
      { path: "/login", element: <LoginPage /> },
      { path: "/register", element: <RegisterPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    errorElement: <ErrorPage />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/dashboard", element: <DashboardPage /> },
          { path: "/children", element: <ChildrenListPage /> },
          { path: "/children/new", element: <AddChildPage /> },
          { path: "/children/:childId", element: <ChildDetailPage /> },
          { path: "/children/:childId/edit", element: <EditChildPage /> },
          { path: "/children/:childId/assessment/intro", element: <AssessmentIntroPage /> },
          { path: "/children/:childId/assessments", element: <AssessmentHistoryPage /> },
          { path: "/children/:childId/reports", element: <ReportHistoryPage /> },
          { path: "/children/:childId/weekly-plan", element: <WeeklyPlanPage /> },
          { path: "/children/:childId/reassessment", element: <ReassessmentPage /> },
          { path: "/assessments/:assessmentId/take", element: <AssessmentTakePage /> },
          { path: "/assessments/:assessmentId/result", element: <AssessmentResultPage /> },
          { path: "/reports/:reportId", element: <ReportPage /> },
          { path: "/followups/:followupId", element: <FollowupDetailPage /> },
          { path: "/profile", element: <ProfilePage /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
