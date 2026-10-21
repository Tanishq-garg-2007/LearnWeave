import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/api";
import type { NoteItem } from "@/api/types";
import { GlassCard } from "@/components/ui/GlassCard";
import { ArrowLeft, Layers, FileText, Globe, Lock, RotateCw } from "lucide-react";

export default function NoteDetailPage(): JSX.Element {
  const { noteId } = useParams<{ noteId: string }>();
  const [note, setNote] = useState<NoteItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!noteId) return;
    setIsLoading(true);
    api
      .getNoteById(noteId)
      .then((data) => setNote(data))
      .catch((err) => setError(err?.message || "Failed to load note details."))
      .finally(() => setIsLoading(false));
  }, [noteId]);

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <RotateCw className="w-8 h-8 text-muted animate-spin" />
        <p className="text-xs font-semibold text-muted">Loading note chunks...</p>
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="py-16 text-center space-y-4">
        <p className="text-sm text-danger font-semibold">{error || "Note not found."}</p>
        <Link to="/notes" className="text-xs text-cyan-800 underline font-semibold">
          Return to Notes
        </Link>
      </div>
    );
  }

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-6 text-left animate-in fade-in duration-200">
      <Link
        to="/notes"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to My Notes</span>
      </Link>

      {/* Note Header Card */}
      <div className="rounded-3xl p-6 sm:p-8 bg-white/80 border border-white/90 shadow-glass backdrop-blur-xl space-y-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100 text-cyan-800">
            {note.subject || "General"}
          </span>
          <span className="text-xs text-muted flex items-center gap-1">
            {note.is_public ? (
              <>
                <Globe className="w-3.5 h-3.5 text-cyan-600" />
                <span>Public Note</span>
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5 text-muted" />
                <span>Private Workspace</span>
              </>
            )}
          </span>
        </div>

        <h1 className="text-2xl font-bold text-ink">{note.title}</h1>

        <div className="flex items-center gap-4 text-xs text-muted pt-1">
          <span className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" />
            {note.chunk_count} Semantic Chunks
          </span>
          <span>•</span>
          <span className="uppercase font-mono text-[11px]">{note.file_type}</span>
          <span>•</span>
          <span>Uploaded {new Date(note.created_at).toLocaleDateString()}</span>
        </div>
      </div>

      {/* Chunks List */}
      <div className="space-y-4">
        <h2 className="text-base font-bold text-ink">Semantic Chunks & Dense Embeddings</h2>

        {(!note.chunks || note.chunks.length === 0) ? (
          <div className="p-8 rounded-2xl bg-white/60 border border-surface-border text-center text-xs text-muted">
            Chunk details are being indexed.
          </div>
        ) : (
          <div className="space-y-3">
            {note.chunks.map((chunk) => (
              <div
                key={chunk.id}
                className="p-5 rounded-2xl bg-white border border-surface-border shadow-xs space-y-2 text-left"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono font-bold text-[11px] text-muted">
                    Chunk #{chunk.chunk_index}
                  </span>
                  <span className="text-[10px] font-mono text-muted/60">{chunk.id}</span>
                </div>
                <p className="text-xs text-text/85 leading-relaxed whitespace-pre-wrap font-sans">
                  {chunk.content}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
