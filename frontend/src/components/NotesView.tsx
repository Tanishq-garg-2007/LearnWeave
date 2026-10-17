import React, { useState, useEffect } from "react";
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
  CheckCircle2
} from "lucide-react";
import { api, NoteItem } from "../api/client";

interface NotesViewProps {
  onRefreshRoadmap?: () => void;
}

export const NotesView: React.FC<NotesViewProps> = () => {
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedNote, setSelectedNote] = useState<NoteItem | null>(null);
  const [isPublicUpload, setIsPublicUpload] = useState(false);
  const [uploadSubject, setUploadSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchNotes = async () => {
    setIsLoading(true);
    try {
      const data = await api.listNotes();
      setNotes(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || "Failed to load notes");
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
    setSuccessMsg(null);

    try {
      const uploaded = await api.uploadNote(file, isPublicUpload, uploadSubject || "General");
      setSuccessMsg(`Note "${uploaded.title}" uploaded and split into ${uploaded.chunk_count} semantic chunks.`);
      await fetchNotes();
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setIsUploading(false);
      // Reset input value
      e.target.value = "";
    }
  };

  const handleDelete = async (noteId: string) => {
    if (!confirm("Are you sure you want to delete this note and all its embeddings?")) return;
    try {
      await api.deleteNote(noteId);
      if (selectedNote?.id === noteId) setSelectedNote(null);
      await fetchNotes();
    } catch (err: any) {
      setError(err.message || "Failed to delete note");
    }
  };

  const handleTogglePublish = async (note: NoteItem) => {
    try {
      const res = await api.publishNote(note.id, !note.is_public);
      setNotes((prev) =>
        prev.map((n) => (n.id === note.id ? { ...n, is_public: res.is_public } : n))
      );
    } catch (err: any) {
      setError(err.message || "Failed to toggle visibility");
    }
  };

  const viewNoteDetails = async (noteId: string) => {
    try {
      const detail = await api.getNoteById(noteId);
      setSelectedNote(detail);
    } catch (err: any) {
      setError(err.message || "Failed to load chunk details");
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Header Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-8 bg-gradient-to-br from-slate-900 via-indigo-950/30 to-slate-900 border border-slate-800 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Workspace Knowledge Base
              </span>
              <span className="text-xs text-slate-400">pgvector Dense Embeddings (384-d ONNX)</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Study Notes & Hybrid RAG Index
            </h1>
            <p className="mt-2 text-sm text-slate-400 max-w-xl">
              Upload your lecture notes, PDFs, or textbooks. LearnWeave automatically indexes semantic chunks
              with local ONNX embeddings for grounded lesson synthesis and fact verification.
            </p>
          </div>

          {/* Upload Widget */}
          <div className="glass-panel p-5 rounded-2xl border border-slate-800 w-full md:w-80 flex-shrink-0">
            <h3 className="text-xs font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
              <Upload className="w-4 h-4 text-indigo-400" />
              <span>Upload Document</span>
            </h3>

            <label className="flex flex-col items-center justify-center p-4 border-2 border-dashed border-indigo-500/40 hover:border-indigo-400 rounded-xl cursor-pointer bg-slate-900/60 hover:bg-slate-900 transition-all text-center group">
              <FileText className="w-8 h-8 text-indigo-400 group-hover:scale-110 transition-transform mb-2" />
              <span className="text-xs font-semibold text-slate-200">
                {isUploading ? "Chunking & Embedding..." : "Select PDF, Markdown, or TXT"}
              </span>
              <span className="text-[10px] text-slate-500 mt-1">Up to 25MB • Overlapping Semantic Chunks</span>
              <input
                type="file"
                accept=".pdf,.md,.markdown,.txt"
                onChange={handleFileUpload}
                disabled={isUploading}
                className="hidden"
              />
            </label>

            <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
              <span className="text-[11px]">Publish to Community:</span>
              <button
                type="button"
                onClick={() => setIsPublicUpload(!isPublicUpload)}
                className={`text-[11px] px-2 py-0.5 rounded font-medium border transition-colors ${
                  isPublicUpload
                    ? "bg-indigo-500/20 text-indigo-300 border-indigo-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
              >
                {isPublicUpload ? "Public (Shared)" : "Private (Only You)"}
              </button>
              <input
                type="text"
                value={uploadSubject}
                maxLength={255}
                onChange={(e) => setUploadSubject(e.target.value)}
                placeholder="Subject (e.g. Operating Systems)"
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
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

      {/* Main Content Grid: Notes List + Chunk Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Notes Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-indigo-400" />
              <span>Your Indexed Notes ({notes.length})</span>
            </h2>
          </div>

          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-16 glass-panel rounded-2xl border border-slate-800">
              <div className="w-8 h-8 border-3 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <p className="text-xs text-slate-400 mt-3">Loading private knowledge base...</p>
            </div>
          ) : notes.length === 0 ? (
            <div className="glass-panel rounded-2xl p-8 border border-slate-800 text-center">
              <FileText className="w-10 h-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-bold text-slate-300">No study notes uploaded yet</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Upload course slides, summaries, or reading material to ground lessons with citations to your own notes.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {notes.map((note) => (
                <div
                  key={note.id}
                  className={`glass-panel p-4 rounded-xl border transition-all flex items-center justify-between gap-4 ${
                    selectedNote?.id === note.id
                      ? "border-indigo-500/60 bg-indigo-950/20 shadow-md shadow-indigo-950/40"
                      : "border-slate-800/80 hover:border-slate-700 bg-slate-900/60"
                  }`}
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="p-2.5 rounded-lg bg-indigo-600/10 text-indigo-400 border border-indigo-500/20 mt-0.5">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-sm font-bold text-white truncate">{note.title}</h4>
                      <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-slate-400">
                        <span className="uppercase font-mono text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">
                          {note.file_type}
                        </span>
                        <span>•</span>
                        <span>{note.chunk_count} chunks</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          {note.is_public ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <Globe className="w-3 h-3" /> Public
                            </span>
                          ) : (
                            <span className="text-slate-400 flex items-center gap-1">
                              <Lock className="w-3 h-3" /> Private
                            </span>
                          )}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => viewNoteDetails(note.id)}
                      className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                      title="Inspect Semantic Chunks"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleTogglePublish(note)}
                      className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                      title={note.is_public ? "Make Private" : "Publish to Community"}
                    >
                      <Globe className={`w-4 h-4 ${note.is_public ? "text-indigo-400" : ""}`} />
                    </button>
                    <button
                      onClick={() => handleDelete(note.id)}
                      className="p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 transition-colors"
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

        {/* Right Column: Chunk Inspector */}
        <div className="space-y-4">
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <span>Chunk Inspector</span>
          </h2>

          {selectedNote ? (
            <div className="glass-panel p-5 rounded-2xl border border-slate-800/80 space-y-4 max-h-[600px] overflow-y-auto">
              <div>
                <h3 className="text-sm font-bold text-white">{selectedNote.title}</h3>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Showing {selectedNote.chunks?.length || selectedNote.chunk_count} semantic chunks with 384-d dense vectors.
                </p>
              </div>

              <div className="space-y-3">
                {selectedNote.chunks && selectedNote.chunks.length > 0 ? (
                  selectedNote.chunks.map((chk) => (
                    <div
                      key={chk.id}
                      className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs space-y-1.5"
                    >
                      <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                        <span>Chunk #{chk.chunk_index}</span>
                        <span>ID: {chk.id.slice(0, 8)}...</span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed line-clamp-4 hover:line-clamp-none transition-all">
                        {chk.content}
                      </p>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-slate-500 italic">No chunks loaded for this note.</p>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-panel p-8 rounded-2xl border border-slate-800 text-center">
              <Eye className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">Click the eye icon on any note to inspect its semantic chunks.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
