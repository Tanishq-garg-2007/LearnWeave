import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthProvider";
import { Spinner } from "@/components/ui/Spinner";

export interface GuestOnlyProps {
  children?: React.ReactNode;
}

export function GuestOnly({ children }: GuestOnlyProps): JSX.Element {
  const { status } = useAuth();

  if (status === "loading") {
    return (
      <div className="min-h-[50vh] flex items-center justify-center">
        <Spinner size="lg" label="Checking session..." />
      </div>
    );
  }

  if (status === "authenticated") {
    return <Navigate to="/dashboard" replace />;
  }

  return children ? <>{children}</> : <Outlet />;
}

export default GuestOnly;
