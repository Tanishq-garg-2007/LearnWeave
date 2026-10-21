import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "@/api";
import type { NoteItem } from "@/api/types";
import { GlassCard } from "@/components/ui/GlassCard";
import { useToast } from "@/components/ui/Toast";
import {
  Upload,
  FileText,
  Trash2,
  Globe,
  Lock,
  Layers,
  Sparkles,
  AlertCircle,
  Eye,
  CheckCircle2,
  RotateCw,
  Search,
} from "lucide-react";

export default function NotesPage(): JSX.Element {
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSubject, setUploadSubject] = useState("");
  const [isPublicUpload, setIsPublicUpload] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");
  const [selectedNoteForModal, setSelectedNoteForModal] = useState<NoteItem | null>(null);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  const fetchNotes = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.listNotes();
      setNotes(data || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load study notes.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchNotes();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const uploaded = await api.uploadNote(
        file,
        isPublicUpload,
        uploadSubject.trim() || "General"
      );
      toast.success(
        `Uploaded "${uploaded.title}" and created ${uploaded.chunk_count} semantic vector chunks!`
      );
      await fetchNotes();
      setUploadSubject("");
    } catch (err: any) {
      toast.error(err?.message || "Note upload failed.");
      setError(err?.message || "Upload failed.");
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (noteId: string, noteTitle: string) => {
    if (!confirm(`Are you sure you want to delete "${noteTitle}" and all its vector embeddings?`)) {
      return;
    }

    try {
      await api.deleteNote(noteId);
      toast.success("Note and vector embeddings deleted.");
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
      if (selectedNoteForModal?.id === noteId) setSelectedNoteForModal(null);
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete note.");
    }
  };

  const handleTogglePublish = async (note: NoteItem) => {
    try {
      const res = await api.publishNote(note.id, !note.is_public);
      setNotes((prev) =>
        prev.map((n) => (n.id === note.id ? { ...n, is_public: res.is_public } : n))
      );
      toast.success(
        res.is_public
          ? "Note published to Community Library!"
          : "Note moved to private workspace."
      );
    } catch (err: any) {
      toast.error(err?.message || "Failed to change note visibility.");
    }
  };

  const filteredNotes = notes.filter((n) => {
    const q = searchFilter.toLowerCase();
    return (
      n.title.toLowerCase().includes(q) ||
      (n.subject && n.subject.toLowerCase().includes(q))
    );
  });

  return (
    <div className="py-6 sm:py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto space-y-8 text-left animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2 max-w-xl">
          <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-cyan-100/90 text-cyan-800 border border-cyan-200/80 shadow-xs">
            RAG Knowledge Base
          </span>
          <h1 className="text-2xl sm:text-3xl font-display text-ink font-semibold tracking-tight">
            Study Notes & Ingested Documents
          </h1>
          <p className="text-xs sm:text-sm text-muted">
            Uploaded PDF and plain text documents are semantically chunked and indexed into pgvector.
            Lessons and AI tutors ground their explanations directly in these materials.
          </p>
        </div>

        <div className="text-right">
          <p className="text-3xl font-display font-bold font-mono text-ink">{notes.length}</p>
          <p className="text-[11px] text-muted font-medium">Ingested Documents</p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Upload Zone */}
      <div className="rounded-3xl p-6 sm:p-8 bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl space-y-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-[#252229] text-white flex items-center justify-center shadow-soft">
            <Upload className="w-5 h-5 text-cyan-300" />
          </div>
          <div>
            <h3 className="text-base font-bold text-ink">Upload Course Note or Lecture Slides</h3>
            <p className="text-xs text-muted">
              Supported formats: PDF (.pdf), Text (.txt, .md). Files are parsed and converted to dense embeddings.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          {/* Subject Field */}
          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Subject / Topic
            </label>
            <input
              type="text"
              placeholder="e.g. Distributed Systems, Neural Nets"
              value={uploadSubject}
              onChange={(e) => setUploadSubject(e.target.value)}
              className="w-full px-4 py-2.5 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
            />
          </div>

          {/* Visibility Toggle */}
          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Library Visibility
            </label>
            <div className="flex items-center gap-2 pt-1">
              <button
                type="button"
                onClick={() => setIsPublicUpload(false)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                  !isPublicUpload
                    ? "bg-[#252229] text-white shadow-sm"
                    : "bg-black/5 text-muted hover:text-ink"
                }`}
              >
                Private (Only You)
              </button>
              <button
                type="button"
                onClick={() => setIsPublicUpload(true)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all ${
                  isPublicUpload
                    ? "bg-[#252229] text-white shadow-sm"
                    : "bg-black/5 text-muted hover:text-ink"
                }`}
              >
                Public (Community)
              </button>
            </div>
          </div>

          {/* File input button */}
          <div className="flex flex-col justify-end">
            <label
              className={`inline-flex items-center justify-center gap-2 px-6 py-2.5 rounded-full text-xs font-semibold shadow-md transition-all cursor-pointer ${
                isUploading
                  ? "bg-muted text-white cursor-not-allowed"
                  : "bg-[#252229] hover:bg-[#151318] text-white active:scale-95"
              }`}
            >
              {isUploading ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Extracting & Chunking Vectors...</span>
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 text-cyan-300" />
                  <span>Select File to Ingest</span>
                </>
              )}
              <input
                type="file"
                accept=".pdf,.txt,.md"
                disabled={isUploading}
                onChange={handleFileUpload}
                className="hidden"
              />
            </label>
          </div>
        </div>
      </div>

      {/* Ingested Notes List */}
      <div className="space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-ink">My Ingested Materials ({notes.length})</h2>

          {/* Search filter */}
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-muted pointer-events-none" />
            <input
              type="text"
              placeholder="Filter by title or subject..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full pl-9 pr-4 py-2 rounded-2xl bg-white/70 border border-white/80 ring-1 ring-inset ring-white/70 text-ink text-xs focus:outline-none focus:ring-2 focus:ring-focus focus:bg-white"
            />
          </div>
        </div>

        {isLoading ? (
          <div className="py-16 text-center text-xs text-muted">
            <RotateCw className="w-6 h-6 animate-spin mx-auto mb-2 text-muted" />
            Loading notes...
          </div>
        ) : filteredNotes.length === 0 ? (
          <div className="p-12 rounded-3xl bg-white/55 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.08)] ring-1 ring-inset ring-white/80 backdrop-blur-2xl text-center space-y-3">
            <FileText className="w-10 h-10 text-muted mx-auto" />
            <p className="text-sm font-semibold text-ink">No notes match your filter.</p>
            <p className="text-xs text-muted">
              Upload your lecture slides or notes above to begin grounded learning.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredNotes.map((note) => (
              <div
                key={note.id}
                className="rounded-3xl p-5 bg-white/60 hover:bg-white/85 border border-white/85 shadow-[0_16px_40px_-10px_rgba(40,30,60,0.06)] ring-1 ring-inset ring-white/80 backdrop-blur-xl flex flex-col justify-between space-y-4 hover:shadow-soft transition-all text-left group"
              >
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-cyan-100/90 text-cyan-800 border border-cyan-200">
                      {note.subject || "General"}
                    </span>

                    <button
                      type="button"
                      onClick={() => handleTogglePublish(note)}
                      className="inline-flex items-center gap-1 text-[10px] font-semibold text-muted hover:text-ink"
                      title="Click to toggle public / private"
                    >
                      {note.is_public ? (
                        <>
                          <Globe className="w-3 h-3 text-cyan-600" />
                          <span>Public</span>
                        </>
                      ) : (
                        <>
                          <Lock className="w-3 h-3 text-muted" />
                          <span>Private</span>
                        </>
                      )}
                    </button>
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

                <div className="pt-3 border-t border-surface-border/60 flex items-center justify-between">
                  <Link
                    to={`/notes/${note.id}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-cyan-800 hover:text-ink"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    <span>Inspect Chunks</span>
                  </Link>

                  <button
                    type="button"
                    onClick={() => handleDelete(note.id, note.title)}
                    className="p-1.5 rounded-lg text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                    title="Delete Note"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
