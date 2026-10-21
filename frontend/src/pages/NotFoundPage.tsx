import React from "react";
import { Link } from "react-router-dom";
import { GlassCard } from "@/components/ui/GlassCard";
import { Button } from "@/components/ui/Button";

export default function NotFoundPage(): JSX.Element {
  return (
    <div className="container mx-auto px-4 py-16 max-w-lg text-center">
      <GlassCard padding="lg" className="space-y-4">
        <span className="text-5xl font-mono font-bold text-ink">404</span>
        <h1 className="text-2xl font-bold font-sans text-text">Page Not Found</h1>
        <p className="text-muted text-sm leading-relaxed">
          The learning path or resource you are looking for does not exist or may have been moved.
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
