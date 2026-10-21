import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import type { NoteItem } from "@/api/types";
import { GlassCard } from "@/components/ui/GlassCard";
import { useToast } from "@/components/ui/Toast";
import {
  Globe,
  ThumbsUp,
  ThumbsDown,
  Download,
  Flag,
  Search,
  Sparkles,
  ShieldCheck,
  RotateCw,
  AlertCircle,
  Eye,
  Layers,
  TrendingUp,
} from "lucide-react";

export default function CommunityPage(): JSX.Element {
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<"wilson" | "latest">("wilson");
  const [importingId, setImportingId] = useState<string | null>(null);
  const [reportingId, setReportingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  const fetchCommunityNotes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getCommunityNotes(sortOrder, searchQuery.trim() || undefined);
      setNotes(data || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load community notes.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCommunityNotes();
  }, [sortOrder]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCommunityNotes();
  };

  const handleVote = async (noteId: string, voteType: "upvote" | "downvote") => {
    try {
      const res = await api.voteCommunityNote(noteId, voteType);
      setNotes((prev) =>
        prev.map((n) =>
          n.id === noteId
            ? {
                ...n,
                wilson_score: res.new_wilson_score,
                upvotes: res.upvotes,
                downvotes: res.downvotes,
              }
            : n
        )
      );
      toast.success(voteType === "upvote" ? "Upvoted note!" : "Downvoted note");
    } catch (err: any) {
      toast.error(err?.message || "Failed to register vote.");
    }
  };

  const handleImport = async (note: NoteItem) => {
    setImportingId(note.id);
    try {
      const res = await api.importCommunityNote(note.id);
      toast.success(
        `Imported "${res.title}" into your private workspace (${res.chunks_imported} chunks cloned independently)!`
      );
    } catch (err: any) {
      toast.error(err?.message || "Failed to import note.");
    } finally {
      setImportingId(null);
    }
  };

  const handleReport = async (noteId: string) => {
    const reason = prompt(
      "Reason for reporting this note (e.g. incorrect factual claims, copyright, offensive content):"
    );
    if (!reason) return;

    setReportingId(noteId);
    try {
      const res = await api.reportCommunityNote(noteId, reason);
      if (res.is_quarantined) {
        toast.success("Thank you. Note reached report threshold and has been quarantined.");
        setNotes((prev) => prev.filter((n) => n.id !== noteId));
      } else {
        toast.success("Report submitted for review.");
      }
    } catch (err: any) {
      toast.error(err?.message || "Failed to submit report.");
    } finally {
      setReportingId(null);
    }
  };

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 text-left animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100/90 text-cyan-800 border border-cyan-200/80 shadow-xs">
            Open Knowledge Exchange
          </span>
          <h1 className="text-2xl sm:text-3xl font-display text-ink font-semibold tracking-tight">
            Community Learning Library
          </h1>
          <p className="text-xs sm:text-sm text-muted">
            Explore peer-published study notes. Notes are ranked via Wilson lower bound confidence
            scoring. Import any public note into your private workspace with independent semantic vector cloning.
          </p>
        </div>

        <div className="text-right">
          <p className="text-3xl font-display font-bold font-mono text-ink">{notes.length}</p>
          <p className="text-[11px] text-muted font-medium">Community Notes</p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3.5 top-3 text-muted pointer-events-none" />
          <input
            type="text"
            placeholder="Search community notes by title or subject..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white shadow-xs"
          />
        </form>

        {/* Sort Controls */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <span className="text-xs text-muted font-medium">Sort:</span>
          <button
            type="button"
            onClick={() => setSortOrder("wilson")}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
              sortOrder === "wilson"
                ? "bg-[#252229] text-white shadow-sm"
                : "bg-white/60 border border-white/80 ring-1 ring-inset ring-white/70 text-muted hover:text-ink backdrop-blur-md"
            }`}
          >
            Wilson Score
          </button>
          <button
            type="button"
            onClick={() => setSortOrder("latest")}
            className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
              sortOrder === "latest"
                ? "bg-[#252229] text-white shadow-sm"
                : "bg-white/60 border border-white/80 ring-1 ring-inset ring-white/70 text-muted hover:text-ink backdrop-blur-md"
            }`}
          >
            Latest
          </button>
        </div>
      </div>

      {/* Notes Grid */}
      {isLoading ? (
        <div className="py-20 text-center text-xs text-muted">
          <RotateCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted" />
          Loading community notes...
        </div>
      ) : notes.length === 0 ? (
        <div className="p-12 rounded-3xl bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-center space-y-3">
          <Globe className="w-10 h-10 text-muted mx-auto" />
          <p className="text-sm font-bold text-ink">No community notes found</p>
          <p className="text-xs text-muted">
            Be the first to publish a study note to the community library from your Notes view.
          </p>
          <Link
            to="/notes"
            className="inline-flex items-center gap-2 px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
          >
            Go to My Notes
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {notes.map((note) => (
            <div
              key={note.id}
              className="rounded-3xl p-5 bg-white/60 hover:bg-white/85 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.06)] ring-1 ring-inset ring-white/80 backdrop-blur-xl flex flex-col justify-between space-y-4 hover:shadow-soft transition-all text-left group"
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-cyan-100/90 text-cyan-800 border border-cyan-200">
                    {note.subject || "General"}
                  </span>
                  <span className="text-[11px] font-mono text-muted flex items-center gap-1 font-semibold">
                    <TrendingUp className="w-3 h-3 text-cyan-600" />
                    Score: {Math.round((note.wilson_score || 0) * 100)}
                  </span>
                </div>

                <h3 className="text-sm font-bold text-ink line-clamp-2 leading-tight group-hover:text-cyan-950 transition-colors">
                  {note.title}
                </h3>

                <div className="flex items-center gap-3 text-[11px] text-muted">
                  <span className="flex items-center gap-1 font-medium">
                    <Layers className="w-3 h-3" />
                    {note.chunk_count} chunks
                  </span>
                  <span>•</span>
                  <span className="uppercase font-mono text-[10px]">{note.file_type}</span>
                </div>
              </div>

              {/* Voting and Actions */}
              <div className="pt-3 border-t border-surface-border/60 flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => handleVote(note.id, "upvote")}
                    className="p-1.5 rounded-lg bg-black/5 hover:bg-emerald-50 hover:text-emerald-700 transition-colors flex items-center gap-1 text-[11px] font-mono font-semibold"
                    title="Upvote"
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                    <span>{note.upvotes || 0}</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleVote(note.id, "downvote")}
                    className="p-1.5 rounded-lg bg-black/5 hover:bg-rose-50 hover:text-rose-700 transition-colors flex items-center gap-1 text-[11px] font-mono font-semibold"
                    title="Downvote"
                  >
                    <ThumbsDown className="w-3.5 h-3.5" />
                    <span>{note.downvotes || 0}</span>
                  </button>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleImport(note)}
                    disabled={importingId === note.id}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-[11px] font-semibold shadow-xs active:scale-95 transition-all"
                  >
                    {importingId === note.id ? (
                      <RotateCw className="w-3 h-3 animate-spin" />
                    ) : (
                      <Download className="w-3 h-3 text-cyan-300" />
                    )}
                    <span>Import</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleReport(note.id)}
                    className="p-1.5 rounded-lg text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                    title="Report Note (Auto-quarantines on threshold)"
                  >
                    <Flag className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
