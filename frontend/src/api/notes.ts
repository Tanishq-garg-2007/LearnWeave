import { request, LLM_TIMEOUT_MS } from "./http";
import type {
  NoteItem,
  NoteChunk,
  NoteUploadResponse,
  NotesSearchResponse,
} from "./types";

interface RawNoteChunk {
  id: string;
  chunk_index: number;
  text_content?: string;
  content?: string;
  page_number?: number;
  created_at?: string;
}

interface RawNote {
  id: string;
  title: string;
  subject?: string;
  tags?: string[];
  file_type?: string;
  file_size?: number;
  visibility?: string;
  processing_status?: string;
  chunk_count?: number;
  upvotes?: number;
  downvotes?: number;
  wilson_score?: number;
  created_at: string;
  updated_at?: string;
  raw_content?: string;
  chunks?: RawNoteChunk[];
}

export function normalizeNote(raw: RawNote): NoteItem {
  const chunks: NoteChunk[] | undefined = Array.isArray(raw.chunks)
    ? raw.chunks.map((c) => ({
        id: c.id,
        chunk_index: c.chunk_index,
        content: c.text_content ?? c.content ?? "",
        page_number: c.page_number,
        created_at: c.created_at,
      }))
    : undefined;

  return {
    id: raw.id,
    title: raw.title,
    subject: raw.subject,
    tags: raw.tags,
    file_type: raw.file_type || "text/plain",
    file_size: raw.file_size,
    visibility: raw.visibility,
    processing_status: raw.processing_status,
    chunk_count: raw.chunk_count ?? chunks?.length ?? 0,
    is_public: raw.visibility === "public",
    upvotes: raw.upvotes ?? 0,
    downvotes: raw.downvotes ?? 0,
    wilson_score: raw.wilson_score ?? 0,
    created_at: raw.created_at,
    updated_at: raw.updated_at,
    raw_content: raw.raw_content,
    chunks,
  };
}

export async function listNotes(): Promise<NoteItem[]> {
  const rawList = await request<RawNote[]>("GET", "/notes");
  return (rawList || []).map(normalizeNote);
}

export async function uploadNote(
  file: File,
  isPublic = false,
  subject = "General"
): Promise<NoteUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("subject", subject.trim() || "General");
  formData.append("visibility", isPublic ? "public" : "private");

  const res = await request<{
    note_id: string;
    title: string;
    subject: string;
    chunks_created?: number;
    status: string;
  }>("POST", "/notes/upload", {
    body: formData,
    timeoutMs: LLM_TIMEOUT_MS,
  });

  return {
    note_id: res.note_id,
    title: res.title,
    subject: res.subject,
    chunks_created: res.chunks_created ?? 0,
    chunk_count: res.chunks_created ?? 0,
    status: res.status,
  };
}

export async function getNoteById(noteId: string): Promise<NoteItem> {
  const raw = await request<RawNote>("GET", `/notes/${noteId}`);
  return normalizeNote(raw);
}

export async function deleteNote(
  noteId: string
): Promise<{ status: string; message: string; id?: string }> {
  return request<{ status: string; message: string; id?: string }>(
    "DELETE",
    `/notes/${noteId}`
  );
}

export async function searchNotes(
  query: string,
  subject?: string,
  top_k = 4
): Promise<NotesSearchResponse> {
  return request<NotesSearchResponse>("POST", "/notes/search", {
    query: {
      query,
      subject,
      top_k,
    },
  });
}
