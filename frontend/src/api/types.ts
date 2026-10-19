// ==========================================
// Authentication & Learner Profile
// ==========================================

export interface LearnerPreferences {
  learning_style?: string;
  explanation_depth?: string;
  daily_minutes?: number;
  analogies_preferred?: boolean;
}

export interface LearnerProfileResponse {
  id: string;
  user_id: string;
  preferences: LearnerPreferences;
  topic_mastery: Record<string, number>;
  weak_areas: string[];
  unresolved_doubts: string[];
  completed_lessons: string[];
}

export interface UserResponse {
  id: string;
  email: string;
  full_name?: string;
  workspace_id?: string | null;
  profile?: LearnerProfileResponse | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  workspace_id: string;
}

export interface UserRegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UpdatePreferencesRequest {
  learning_style?: string;
  explanation_depth?: string;
  daily_minutes?: number;
  analogies_preferred?: boolean;
}

// ==========================================
// Learning Goals & Roadmaps
// ==========================================

export interface GoalCreateRequest {
  subject: string;
  target_level: string;
  current_level: string;
  total_duration_weeks: number;
  hours_per_week: number;
  preferred_style: string;
  specific_objectives: string[];
}

export interface GoalResponse {
  id: string;
  user_id: string;
  subject: string;
  target_level: string;
  current_level: string;
  total_duration_weeks: number;
  hours_per_week: number;
  preferred_style: string;
  specific_objectives: string[];
  created_at: string;
  updated_at?: string;
}

export type LessonStatus = "pending" | "in_progress" | "completed" | "skipped";

export interface LessonResponse {
  id: string;
  module_id: string;
  roadmap_id?: string;
  title: string;
  learning_objectives: string[];
  order_index: number;
  status: LessonStatus;
  duration_minutes: number;
  prerequisites?: string[];
  lesson_content?: Record<string, unknown> | null;
}

export interface ModuleResponse {
  id: string;
  roadmap_id: string;
  title: string;
  description?: string;
  order_index: number;
  is_planned_later: boolean;
  target_week: number;
  estimated_hours: number;
  lessons: LessonResponse[];
}

export interface RoadmapDetailResponse {
  id: string;
  goal_id: string;
  user_id: string;
  title: string;
  version: number;
  is_active: boolean;
  total_modules: number;
  total_lessons: number;
  modules: ModuleResponse[];
  created_at?: string;
  updated_at?: string;
}

export interface RoadmapVersionItem {
  id: string;
  version_number: number;
  change_reason: string;
  created_at: string;
  snapshot_data?: Record<string, unknown>;
}

export interface RescheduleLessonRequest {
  new_status: string;
}

// ==========================================
// Lessons & Content Grounding
// ==========================================

export interface LessonSection {
  title: string;
  explanation: string;
  cited_chunk_ids: string[];
}

export interface LessonStructuredContent {
  sections: LessonSection[];
  key_takeaways: string[];
  grounding_type: string;
  cited_note_ids?: string[];
}

export interface LessonGenerateResponse {
  lesson_id: string;
  title: string;
  status: string;
  grounding_type: string;
  content: LessonStructuredContent | null;
}

export interface LessonDetailView {
  id: string;
  title: string;
  module_id: string;
  module_title?: string | null;
  status: LessonStatus;
  duration_minutes: number;
  learning_objectives: string[];
  content: LessonStructuredContent | null;
}

export interface DoubtRequest {
  doubt: string;
}

export interface DoubtResponse {
  answer: string;
  resolved_citations?: string[];
  related_concept?: string;
  follow_up_prompt?: string;
}

// ==========================================
// Quiz & Automated Evaluation
// ==========================================

export interface NormalizedQuestion {
  id: string;
  question_index: number;
  question_type: string;
  prompt: string;
  options?: string[];
  option_keys?: string[];
  rubric_criteria?: string;
}

export interface NormalizedQuiz {
  quiz_id: string;
  lesson_id: string;
  title: string;
  questions: NormalizedQuestion[];
}

export interface RawQuestionItem {
  question_index: number;
  question_type: string;
  question: string;
  options?: Record<string, string>;
  rubric_criteria?: string;
}

export interface RawQuizResponse {
  assessment_id: string;
  lesson_id: string;
  title: string;
  total_questions?: number;
  questions: RawQuestionItem[];
}

export interface QuizAnswerSubmission {
  question_index: number;
  selected_option?: string;
  written_answer?: string;
}

export interface QuizSubmitRequest {
  assessment_id?: string;
  answers: QuizAnswerSubmission[];
}

export interface QuestionEvaluation {
  question_index: number;
  correct: boolean;
  score: number;
  max_score: number;
  feedback: string;
  rubric_breakdown?: Record<string, unknown>;
}

export interface QuizSubmitResponse {
  attempt_id: string;
  overall_score: number;
  passed: boolean;
  score_percentage: number;
  evaluations: QuestionEvaluation[];
  feedback_summary: string;
  adaptation?: Record<string, unknown>;
}

export interface AssessmentAttemptItem {
  id: string;
  assessment_id: string;
  score: number;
  passed: boolean;
  feedback: string;
  topic_mastery_impact: Record<string, number>;
  created_at: string;
}

// ==========================================
// Notes & RAG Knowledge Ingestion
// ==========================================

export interface NoteChunk {
  id: string;
  chunk_index: number;
  content: string;
  page_number?: number;
  created_at?: string;
}

export interface NoteItem {
  id: string;
  title: string;
  subject?: string;
  tags?: string[];
  file_type: string;
  file_size?: number;
  visibility?: string;
  processing_status?: string;
  chunk_count: number;
  is_public: boolean;
  upvotes: number;
  downvotes: number;
  wilson_score: number;
  created_at: string;
  updated_at?: string;
  raw_content?: string;
  chunks?: NoteChunk[];
}

export interface NoteUploadResponse {
  note_id: string;
  title: string;
  subject: string;
  chunks_created: number;
  chunk_count: number;
  status: string;
}

export interface SearchResultChunk {
  chunk_id: string;
  note_id: string;
  text_content: string;
  score: number;
  metadata?: Record<string, unknown>;
}

export interface NotesSearchResponse {
  query: string;
  count: number;
  results: SearchResultChunk[];
}

// ==========================================
// Study Schedule
// ==========================================

export interface ScheduleItem {
  id: string;
  lesson_id: string;
  lesson_title?: string;
  scheduled_date: string;
  estimated_minutes: number;
  session_type: "standard_lesson" | "spaced_repetition";
  status: "pending" | "completed" | "skipped";
}

// ==========================================
// Community Library
// ==========================================

export interface VoteCommunityNoteResponse {
  upvotes: number;
  downvotes: number;
  wilson_score: number;
  new_wilson_score: number;
}

export interface ImportCommunityNoteResponse {
  status: string;
  new_note_id: string;
  title: string;
  chunks_imported: number;
}

export interface ReportCommunityNoteResponse {
  total_reports: number;
  quarantined: boolean;
  message: string;
  report_count: number;
  is_quarantined: boolean;
}

// ==========================================
// Learning Cycle State Machine
// ==========================================

export interface CycleStateResponse {
  cycle_id: string;
  lesson_id: string;
  current_step: string;
  status?: string;
  completed_steps: string[];
  step_outputs?: Record<string, unknown>;
  context?: Record<string, unknown>;
  is_finished?: boolean;
}

// ==========================================
// Health & Diagnostics
// ==========================================

export interface HealthResponse {
  status: string;
  service?: string;
  version?: string;
}

export interface ReadinessResponse {
  status: string;
  checks: Record<string, boolean>;
  error?: string;
}
