import React, { Suspense, useEffect } from "react";
import {
  createBrowserRouter,
  useLocation,
  useRouteError,
  Link,
} from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";

// Lazy-loaded pages
const LandingPage = React.lazy(() => import("@/pages/LandingPage"));
const LoginPage = React.lazy(() => import("@/pages/LoginPage"));
const RegisterPage = React.lazy(() => import("@/pages/RegisterPage"));
const OnboardingPage = React.lazy(() => import("@/pages/OnboardingPage"));
const DashboardPage = React.lazy(() => import("@/pages/DashboardPage"));
const RoadmapPage = React.lazy(() => import("@/pages/RoadmapPage"));
const LessonDetailPage = React.lazy(() => import("@/pages/LessonDetailPage"));
const NotesPage = React.lazy(() => import("@/pages/NotesPage"));
const NoteDetailPage = React.lazy(() => import("@/pages/NoteDetailPage"));
const SchedulePage = React.lazy(() => import("@/pages/SchedulePage"));
const CommunityPage = React.lazy(() => import("@/pages/CommunityPage"));
const CommunityNoteDetailPage = React.lazy(() => import("@/pages/CommunityNoteDetailPage"));
const ProfilePage = React.lazy(() => import("@/pages/ProfilePage"));
const GoalsPage = React.lazy(() => import("@/pages/GoalsPage"));
const RoadmapHistoryPage = React.lazy(() => import("@/pages/RoadmapHistoryPage"));
const NotFoundPage = React.lazy(() => import("@/pages/NotFoundPage"));
const UiShowcase = React.lazy(() => import("@/pages/UiShowcase"));

export function PageFallback(): JSX.Element {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl space-y-4">
      <Skeleton className="h-8 w-48 rounded-full" />
      <Skeleton className="h-40 w-full rounded-3xl" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-32 rounded-3xl" />
        <Skeleton className="h-32 rounded-3xl" />
      </div>
    </div>
  );
}

export function RouteErrorElement(): JSX.Element {
  const error = useRouteError();
  console.error("Route error:", error);

  return (
    <div className="container mx-auto px-4 py-16 max-w-lg text-center">
      <GlassCard padding="lg" className="space-y-4">
        <h1 className="text-2xl font-bold font-sans text-text">Something went wrong</h1>
        <p className="text-muted text-sm leading-relaxed">
          We encountered an unexpected error while loading this page.
        </p>
        <div className="pt-2">
          <Link to="/dashboard">
            <Button variant="primary">Go to Dashboard</Button>
          </Link>
        </div>
      </GlassCard>
    </div>
  );
}

function RoutePageContainer({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}): JSX.Element {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);

  useEffect(() => {
    document.title = `${title} · LearnWeave`;
  }, [title]);

  return <Suspense fallback={<PageFallback />}>{children}</Suspense>;
}

function RootLayout(): JSX.Element {
  return <AppShell />;
}

// 16 canonical application routes
const baseRoutes = [
  {
    path: "/",
    element: (
      <RoutePageContainer title="Home">
        <LandingPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/login",
    element: (
      <RoutePageContainer title="Sign In">
        <LoginPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/register",
    element: (
      <RoutePageContainer title="Create Account">
        <RegisterPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/onboarding",
    element: (
      <RoutePageContainer title="Set Goal">
        <OnboardingPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/dashboard",
    element: (
      <RoutePageContainer title="Dashboard">
        <DashboardPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/roadmap",
    element: (
      <RoutePageContainer title="Roadmap">
        <RoadmapPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/lessons/:lessonId",
    element: (
      <RoutePageContainer title="Lesson">
        <LessonDetailPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/notes",
    element: (
      <RoutePageContainer title="Notes">
        <NotesPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/notes/:noteId",
    element: (
      <RoutePageContainer title="Note Detail">
        <NoteDetailPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/schedule",
    element: (
      <RoutePageContainer title="Schedule">
        <SchedulePage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/community",
    element: (
      <RoutePageContainer title="Community">
        <CommunityPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/community/:noteId",
    element: (
      <RoutePageContainer title="Community Note">
        <CommunityNoteDetailPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/profile",
    element: (
      <RoutePageContainer title="Profile">
        <ProfilePage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/goals",
    element: (
      <RoutePageContainer title="Goals">
        <GoalsPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "/roadmaps/:roadmapId/history",
    element: (
      <RoutePageContainer title="Roadmap History">
        <RoadmapHistoryPage />
      </RoutePageContainer>
    ),
  },
  {
    path: "*",
    element: (
      <RoutePageContainer title="404 Not Found">
        <NotFoundPage />
      </RoutePageContainer>
    ),
  },
];

// Add /__ui showcase only in development
const devRoutes = import.meta.env.DEV
  ? [
      {
        path: "/__ui",
        element: (
          <RoutePageContainer title="UI Showcase">
            <UiShowcase />
          </RoutePageContainer>
        ),
      },
    ]
  : [];

export const router = createBrowserRouter([
  {
    element: <RootLayout />,
    errorElement: <RouteErrorElement />,
    children: [...baseRoutes, ...devRoutes],
  },
]);

export default router;
