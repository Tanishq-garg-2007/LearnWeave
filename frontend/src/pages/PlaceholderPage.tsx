import React from "react";
import { GlassCard } from "@/components/ui/GlassCard";
import { Badge } from "@/components/ui/Badge";

export interface PlaceholderPageProps {
  title: string;
  batch: string;
  description?: string;
}

export function PlaceholderPage({ title, batch, description }: PlaceholderPageProps): JSX.Element {
  return (
    <div className="container mx-auto px-4 py-12 max-w-4xl">
      <GlassCard padding="lg" className="text-center space-y-4">
        <div className="inline-flex justify-center">
          <Badge variant="accent">{batch}</Badge>
        </div>
        <h1 className="text-3xl sm:text-4xl font-display text-text">{title}</h1>
        <p className="text-muted text-sm max-w-md mx-auto">
          {description || `${title} module is scheduled for implementation in ${batch}.`}
        </p>
      </GlassCard>
    </div>
  );
}

export default PlaceholderPage;
