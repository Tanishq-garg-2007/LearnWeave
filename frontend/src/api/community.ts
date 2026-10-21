import { request, LLM_TIMEOUT_MS } from "./http";
import { normalizeNote } from "./notes";
import type {
  NoteItem,
  VoteCommunityNoteResponse,
  ImportCommunityNoteResponse,
  ReportCommunityNoteResponse,
} from "./types";

export async function getCommunityNotes(
  sort: "wilson" | "latest" | "upvotes" = "wilson",
  search?: string
): Promise<NoteItem[]> {
  const query: Record<string, string> = { sort_by: sort };
  if (search) query.query = search;

  const res = await request<NoteItem[] | { notes: NoteItem[] }>("GET", "/community/notes", {
    query,
  });

  const rawList = Array.isArray(res) ? res : res.notes || [];
  return rawList.map(normalizeNote);
}

export async function voteCommunityNote(
  noteId: string,
  voteType: "upvote" | "downvote"
): Promise<VoteCommunityNoteResponse> {
  return request<VoteCommunityNoteResponse>("POST", `/community/notes/${noteId}/vote`, {
    body: { vote_value: voteType === "upvote" ? 1 : -1 },
  });
}

export async function importCommunityNote(noteId: string): Promise<ImportCommunityNoteResponse> {
  return request<ImportCommunityNoteResponse>("POST", `/community/notes/${noteId}/import`, {
    timeoutMs: LLM_TIMEOUT_MS,
  });
}

export async function reportCommunityNote(
  noteId: string,
  reason = "Inappropriate or inaccurate content"
): Promise<ReportCommunityNoteResponse> {
  const res = await request<{ total_reports: number; quarantined: boolean; message: string }>(
    "POST",
    `/community/notes/${noteId}/report`,
    {
      body: { reason },
    }
  );
  return {
    ...res,
    report_count: res.total_reports,
    is_quarantined: res.quarantined,
  };
}

export async function publishNote(
  noteId: string,
  isPublic: boolean
): Promise<{ id: string; visibility: string; is_public: boolean }> {
  const res = await request<{ id: string; visibility: string }>(
    "PUT",
    `/community/notes/${noteId}/publish`,
    {
      body: { visibility: isPublic ? "public" : "private" },
    }
  );
  return {
    ...res,
    is_public: res.visibility === "public",
  };
}
