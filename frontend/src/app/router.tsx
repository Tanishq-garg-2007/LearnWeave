import React, { Suspense, useEffect } from "react";
import {
  createBrowserRouter,
  useLocation,
  useRouteError,
  Link,
} from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth, GuestOnly } from "@/features/auth";
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
      <GuestOnly>
        <RoutePageContainer title="Sign In">
          <LoginPage />
        </RoutePageContainer>
      </GuestOnly>
    ),
  },
  {
    path: "/register",
    element: (
      <GuestOnly>
        <RoutePageContainer title="Create Account">
          <RegisterPage />
        </RoutePageContainer>
      </GuestOnly>
    ),
  },
  {
    path: "/onboarding",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Set Goal">
          <OnboardingPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/dashboard",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Dashboard">
          <DashboardPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/roadmap",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Roadmap">
          <RoadmapPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/lessons/:lessonId",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Lesson">
          <LessonDetailPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/notes",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Notes">
          <NotesPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/notes/:noteId",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Note Detail">
          <NoteDetailPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/schedule",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Schedule">
          <SchedulePage />
        </RoutePageContainer>
      </RequireAuth>
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
      <RequireAuth>
        <RoutePageContainer title="Profile">
          <ProfilePage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/goals",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Goals">
          <GoalsPage />
        </RoutePageContainer>
      </RequireAuth>
    ),
  },
  {
    path: "/roadmaps/:roadmapId/history",
    element: (
      <RequireAuth>
        <RoutePageContainer title="Roadmap History">
          <RoadmapHistoryPage />
        </RoutePageContainer>
      </RequireAuth>
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
