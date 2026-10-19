import React from "react";
import { Navigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { Spinner } from "@/components/ui/Spinner";

export interface RequireAuthProps {
  children?: React.ReactNode;
}

export function RequireAuth({ children }: RequireAuthProps): JSX.Element {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "loading") {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <Spinner size="lg" label="Checking session..." />
      </div>
    );
  }

  if (status === "guest") {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}

export default RequireAuth;
