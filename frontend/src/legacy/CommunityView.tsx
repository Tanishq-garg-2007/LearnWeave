import React, { useState, useEffect } from "react";
import {
  Globe,
  ThumbsUp,
  ThumbsDown,
  Download,
  Flag,
  Search,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Clock
} from "lucide-react";
import { api, NoteItem } from "../api/client";

interface CommunityViewProps {
  onNoteImported?: () => void;
}

export const CommunityView: React.FC<CommunityViewProps> = ({ onNoteImported }) => {
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortOrder, setSortOrder] = useState<"wilson" | "latest">("wilson");
  const [importingId, setImportingId] = useState<string | null>(null);
  const [reportingId, setReportingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchCommunityNotes = async () => {
    setIsLoading(true);
    try {
      const data = await api.getCommunityNotes(sortOrder, searchQuery || undefined);
      setNotes(Array.isArray(data) ? data : ((data as any)?.notes || []));
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load community notes");
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
    } catch (err: any) {
      setError(err.message || "Failed to register vote");
    }
  };

  const handleImport = async (note: NoteItem) => {
    setImportingId(note.id);
    setError(null);
    setSuccessMsg(null);
    try {
      const res = await api.importCommunityNote(note.id);
      setSuccessMsg(
        `Imported "${res.title}" into your private workspace (${res.chunks_imported} chunks cloned independently).`
      );
      if (onNoteImported) onNoteImported();
    } catch (err: any) {
      setError(err.message || "Failed to import note");
    } finally {
      setImportingId(null);
    }
  };

  const handleReport = async (noteId: string) => {
    const reason = prompt("Please provide a reason for reporting this note (e.g. incorrect facts, offensive content):");
    if (!reason) return;

    setReportingId(noteId);
    try {
      const res = await api.reportCommunityNote(noteId, reason);
      if (res.is_quarantined) {
        setSuccessMsg("Thank you. Note has reached the report threshold and has been quarantined from the public feed.");
        setNotes((prev) => prev.filter((n) => n.id !== noteId));
      } else {
        setSuccessMsg(`Report registered (${res.report_count}/3 reports recorded).`);
      }
    } catch (err: any) {
      setError(err.message || "Failed to report note");
    } finally {
      setReportingId(null);
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-gradient-to-br from-slate-900 via-purple-950/20 to-slate-900 border border-slate-800 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Peer Knowledge Exchange
              </span>
              <span className="text-xs text-slate-400">95% Wilson Score Ranking Algorithm</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Global Community Library
            </h1>
            <p className="mt-2 text-sm text-slate-400 max-w-xl">
              Discover, rate, and clone high-yield study materials created by other students.
              Cloning copies the text and embeddings into your private workspace so your study pipeline remains intact
              even if the original note changes.
            </p>
          </div>

          {/* Search & Sort Controls */}
          <div className="w-full md:w-80 flex flex-col gap-3">
            <form onSubmit={handleSearchSubmit} className="relative">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search community notes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </form>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setSortOrder("wilson")}
                className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                  sortOrder === "wilson"
                    ? "bg-purple-600 text-white border-purple-500 shadow-lg shadow-purple-600/20"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                <TrendingUp className="w-3.5 h-3.5" />
                <span>Wilson Ranked</span>
              </button>

              <button
                type="button"
                onClick={() => setSortOrder("latest")}
                className={`flex-1 py-2 px-3 rounded-xl text-xs font-semibold flex items-center justify-center gap-1.5 border transition-all ${
                  sortOrder === "latest"
                    ? "bg-purple-600 text-white border-purple-500 shadow-lg shadow-purple-600/20"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                <Clock className="w-3.5 h-3.5" />
                <span>Most Recent</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-xs font-bold hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* Community Notes Grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 glass-panel rounded-3xl border border-slate-800">
          <div className="w-8 h-8 border-3 border-purple-500/30 border-t-purple-500 rounded-full animate-spin" />
          <p className="text-xs text-slate-400 mt-3">Fetching community index & Wilson scores...</p>
        </div>
      ) : notes.length === 0 ? (
        <div className="glass-panel rounded-3xl p-12 border border-slate-800 text-center max-w-lg mx-auto">
          <Globe className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white">No Public Community Notes Found</h3>
          <p className="text-xs text-slate-400 mt-2">
            Be the first to share! Upload a study note in your Notes tab and toggle its visibility to "Public".
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {notes.map((note) => {
            const isImporting = importingId === note.id;
            const isReporting = reportingId === note.id;

            return (
              <div
                key={note.id}
                className="glass-panel rounded-2xl p-5 border border-slate-800/80 hover:border-purple-500/40 transition-all flex flex-col justify-between space-y-4 group bg-slate-900/60"
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="uppercase text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                      {note.file_type}
                    </span>

                    {/* Wilson Score Badge */}
                    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-[11px] text-purple-300 font-mono font-bold">
                      <Sparkles className="w-3 h-3 text-purple-400" />
                      <span>{(note.wilson_score * 100).toFixed(1)}% Wilson</span>
                    </div>
                  </div>

                  <h3 className="text-base font-bold text-white group-hover:text-purple-300 transition-colors line-clamp-2">
                    {note.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    {note.chunk_count} semantic chunks • 384-d dense embeddings
                  </p>
                </div>

                {/* Footer Controls: Votes, Clone, Report */}
                <div className="pt-3 border-t border-slate-800/60 flex items-center justify-between gap-2">
                  {/* Upvote / Downvote */}
                  <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 border border-slate-800">
                    <button
                      type="button"
                      onClick={() => handleVote(note.id, "upvote")}
                      className="p-1 rounded text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                      title="Upvote note"
                    >
                      <ThumbsUp className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-[11px] font-mono text-slate-300 px-1">
                      {note.upvotes - note.downvotes}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleVote(note.id, "downvote")}
                      className="p-1 rounded text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Downvote note"
                    >
                      <ThumbsDown className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Report */}
                    <button
                      type="button"
                      onClick={() => handleReport(note.id)}
                      disabled={isReporting}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                      title="Report note (3 reports automatically quarantines)"
                    >
                      <Flag className="w-3.5 h-3.5" />
                    </button>

                    {/* Import Button */}
                    <button
                      type="button"
                      onClick={() => handleImport(note)}
                      disabled={isImporting}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs shadow-md shadow-purple-600/20 transition-all hover:scale-105 disabled:opacity-50"
                    >
                      {isImporting ? (
                        <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        <Download className="w-3.5 h-3.5" />
                      )}
                      <span>{isImporting ? "Cloning..." : "Import"}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
