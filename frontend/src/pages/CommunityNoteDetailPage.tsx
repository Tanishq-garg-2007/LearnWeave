import React, { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "@/api";
import type { NoteItem } from "@/api/types";
import { ArrowLeft, Layers, Globe, Download, RotateCw } from "lucide-react";
import { useToast } from "@/components/ui/Toast";

export default function CommunityNoteDetailPage(): JSX.Element {
  const { noteId } = useParams<{ noteId: string }>();
  const [note, setNote] = useState<NoteItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  useEffect(() => {
    if (!noteId) return;
    setIsLoading(true);
    api
      .getNoteById(noteId)
      .then((data) => setNote(data))
      .catch((err) => setError(err?.message || "Failed to load community note."))
      .finally(() => setIsLoading(false));
  }, [noteId]);

  const handleImport = async () => {
    if (!note) return;
    setIsImporting(true);
    try {
      const res = await api.importCommunityNote(note.id);
      toast.success(`Imported "${res.title}" with ${res.chunks_imported} independent vector chunks!`);
    } catch (err: any) {
      toast.error(err?.message || "Failed to import note.");
    } finally {
      setIsImporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center space-y-3">
        <RotateCw className="w-8 h-8 text-muted animate-spin" />
        <p className="text-xs font-semibold text-muted">Loading community note...</p>
      </div>
    );
  }

  if (error || !note) {
    return (
      <div className="py-16 text-center space-y-4">
        <p className="text-sm text-danger font-semibold">{error || "Note not found."}</p>
        <Link to="/community" className="text-xs text-cyan-800 underline font-semibold">
          Return to Community Library
        </Link>
      </div>
    );
  }

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto space-y-6 text-left animate-in fade-in duration-200">
      <Link
        to="/community"
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted hover:text-ink transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Community Library</span>
      </Link>

      <div className="rounded-3xl p-6 sm:p-8 bg-white/80 border border-white/90 shadow-glass backdrop-blur-xl space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100 text-cyan-800">
              {note.subject || "General"}
            </span>
            <h1 className="text-2xl font-bold text-ink">{note.title}</h1>
          </div>

          <button
            type="button"
            onClick={handleImport}
            disabled={isImporting}
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            {isImporting ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5 text-cyan-300" />}
            <span>Import to Private Workspace</span>
          </button>
        </div>

        <div className="flex items-center gap-4 text-xs text-muted pt-2 border-t border-surface-border">
          <span className="flex items-center gap-1">
            <Layers className="w-3.5 h-3.5" />
            {note.chunk_count} Chunks
          </span>
          <span>•</span>
          <span className="uppercase font-mono text-[11px]">{note.file_type}</span>
        </div>
      </div>

      <div className="space-y-3">
        <h2 className="text-base font-bold text-ink">Public Document Chunks</h2>
        {note.chunks?.map((chunk) => (
          <div
            key={chunk.id}
            className="p-5 rounded-2xl bg-white border border-surface-border shadow-xs space-y-2 text-left"
          >
            <span className="font-mono font-bold text-[11px] text-muted">Chunk #{chunk.chunk_index}</span>
            <p className="text-xs text-text/85 leading-relaxed whitespace-pre-wrap">{chunk.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
