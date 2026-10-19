export const queryKeys = {
  auth: {
    me: () => ["auth", "me"] as const,
  },
  roadmaps: {
    all: () => ["roadmaps"] as const,
    active: () => ["roadmaps", "active"] as const,
    detail: (id: string) => ["roadmaps", "detail", id] as const,
    versions: (id: string) => ["roadmaps", "versions", id] as const,
  },
  goals: {
    all: () => ["goals"] as const,
    detail: (id: string) => ["goals", "detail", id] as const,
  },
  lessons: {
    detail: (id: string) => ["lessons", "detail", id] as const,
    quiz: (id: string) => ["lessons", "quiz", id] as const,
    attempts: (id: string) => ["lessons", "attempts", id] as const,
  },
  notes: {
    all: () => ["notes"] as const,
    list: () => ["notes", "list"] as const,
    detail: (id: string) => ["notes", "detail", id] as const,
    search: (query: string, subject?: string) =>
      ["notes", "search", { query, subject }] as const,
  },
  schedule: {
    byRoadmap: (roadmapId: string) => ["schedule", "roadmap", roadmapId] as const,
  },
  community: {
    notes: (sort = "wilson", search?: string) =>
      ["community", "notes", { sort, search }] as const,
  },
  cycle: {
    state: (cycleId: string) => ["cycle", "state", cycleId] as const,
  },
  health: {
    status: () => ["health", "status"] as const,
    readiness: () => ["health", "readiness"] as const,
  },
} as const;

export default queryKeys;
