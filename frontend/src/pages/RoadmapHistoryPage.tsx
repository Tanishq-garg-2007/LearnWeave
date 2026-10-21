import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/api";
import type { RoadmapVersionItem } from "@/api/types";
import { ArrowLeft, History, RotateCw, Calendar, Award } from "lucide-react";

export default function RoadmapHistoryPage(): JSX.Element {
  const { roadmapId } = useParams<{ roadmapId: string }>();
  const [versions, setVersions] = useState<RoadmapVersionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!roadmapId) return;
    setIsLoading(true);
    api
      .getRoadmapVersions(roadmapId)
      .then((data) => setVersions(data || []))
      .catch((err) => setError(err?.message || "Failed to load version history."))
      .finally(() => setIsLoading(false));
  }, [roadmapId]);

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-4xl mx-auto space-y-6 text-left animate-in fade-in duration-200">
      <Link
        to="/roadmap"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Active Roadmap</span>
      </Link>

      <div className="rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100/90 text-cyan-800 border border-cyan-200/80 shadow-xs">
            Roadmap Evolution
          </span>
        </div>
        <h1 className="text-2xl font-bold text-ink">Roadmap Version History</h1>
        <p className="text-xs text-muted">
          Tracks every adaptive reorganization triggered by assessment evaluations and remediation.
        </p>
      </div>

      {isLoading ? (
        <div className="py-16 text-center text-xs text-muted">
          <RotateCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted" />
          Loading version timeline...
        </div>
      ) : versions.length === 0 ? (
        <div className="p-10 rounded-2xl bg-white/55 border border-white/85 ring-1 ring-inset ring-white/80 backdrop-blur-xl text-center text-xs text-muted">
          No previous versions recorded. Currently on initial sprint version v1.
        </div>
      ) : (
        <div className="space-y-3">
          {versions.map((ver) => (
            <div
              key={ver.id}
              className="p-5 rounded-2xl bg-white/60 hover:bg-white/85 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.06)] ring-1 ring-inset ring-white/80 backdrop-blur-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-left transition-all"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold font-mono px-2 py-0.5 rounded bg-black/5 text-ink">
                    v{ver.version_number}
                  </span>
                  <span className="text-xs font-semibold text-ink">
                    {ver.change_reason || "Adaptive Plan Synthesis"}
                  </span>
                </div>
                <p className="text-[11px] text-muted flex items-center gap-1 font-medium">
                  <Calendar className="w-3 h-3" />
                  {new Date(ver.created_at).toLocaleString()}
                </p>
              </div>

              <span className="text-[10px] font-mono text-muted/60">ID: {ver.id.slice(0, 8)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
