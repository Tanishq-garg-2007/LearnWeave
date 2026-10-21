---
doc: prd
status: approved
---

# LearnWeave AI — Product Requirements

An agentic personalized learning platform that orchestrates curriculum planning, hybrid RAG knowledge grounding, local neural voice synthesis, and adaptive remediation for self-directed technical learners.
Source: `scope.md > The Unique Kernel`.

## The Core Journey
1. **Workspace Entry**: The user signs up or logs into their private workspace via JWT credentials; an isolated user directory and database session are established.
2. **Goal & Cognitive Sprint Creation**: The user inputs their learning target and available study hours per day. `RoadmapPlanningAgent` constructs a structured curriculum strictly detailing Weeks 1 and 2, while pacing future modules as locked placeholders.
3. **Note Ingestion & Knowledge Grounding**: The user optionally uploads course PDFs, text notes, or markdown files into their workspace. Files are parsed into semantic chunks and embedded into 384-dimensional dense vectors.
4. **Learning Session Launch**: The user clicks on an active sprint lesson. The platform initializes a persistent session in `cycle_runs` and retrieves knowledge chunks via Reciprocal Rank Fusion ($k=60$) combining pgvector and Full-Text Search.
5. **Interactive Lesson & Vocal Narration**: The lesson is rendered with Markdown formatting. The user clicks "Play Audio" to hear instantaneous 24kHz natural narration synthesized locally in ~55ms via Kokoro-82M ONNX.
6. **Doubt Resolution**: The user asks clarifying questions via text or voice (Whisper STT). The `DoubtAgent` provides empathetic, grounded answers and tracks student weak points in their learner profile.
7. **Formative Assessment & Grading**: The user starts the 4-question quiz (3 MCQs + 1 conceptual short answer). The `EvaluationAgent` deterministically grades the MCQs and applies a pedagogical rubric via LLM to score the short answer. Correct answers remain hidden from client payloads until submission.
8. **Adaptive Remediation / Pacing**: If the quiz score is $\ge 70\%$, the lesson is marked complete, mastery is credited, and spaced repetition review dates (+3d, +7d) are scheduled in the study calendar. If the score is $< 70\%$, the `AdaptiveAgent` inserts a targeted revision lesson into the active sprint.
9. **Community Exchange**: The user can publish their synthesized notes to the global library. The community sorts notes using a 95% Wilson score confidence interval, allowing peer learners to import independent clones into their private workspaces.

## Screens and Layout
- **Dashboard & Goal Manager**: Overview of active learning targets, overall progress percentage, study streak, and quick-launch buttons.
- **Roadmap Sprint Visualizer**: Interactive vertical timeline showing active Weeks 1-2 modules with difficulty badges, estimated durations, completion checks, and locked future sprint nodes.
- **6-Step Learning Cycle Modal**: Focused modal window containing the active step (`lesson_gen`, `doubt`, `quiz_gen`, `eval`, `adaptive`), audio controls, interactive doubt dialogue, and quiz submission form.
- **Notes & Vector Knowledge Hub**: Upload dropzone for lecture files, listing ingested documents, chunk counts, vector indexing status, and privacy toggles.
- **Spaced Repetition Study Calendar**: Daily and weekly calendar view displaying scheduled lesson sessions, spaced repetition reviews, and daily workload limits.
- **Community Notes Library**: Global searchable directory of shared notes with Wilson-ranked vote badges, author attribution, report flags, and one-click clone buttons.

## Look and Feel
- **Theme**: Dark-mode primary workspace (`#090d16` background, `#131b2e` surface cards, `#1e293b` borders).
- **Accents**: Deep Indigo (`#6366f1`) for primary actions, Emerald (`#10b981`) for mastery completions, Amber (`#f59e0b`) for active sprint focus, and Rose (`#f43f5e`) for remediation alerts.
- **Typography**: Inter / Outfit for high-legibility UI text and JetBrains Mono for inline code snippets and formulas.
- **Micro-Interactions**: Subtle border glow on active sprint cards, audio waveform animation during TTS playback, and seamless step progress transitions.

## Features and Behavior

### 1. Active 2-Week Sprint Roadmap
- Only Weeks 1 and 2 contain active, generated lessons.
- Weeks 3+ are generated with `is_planned_later = true` and empty lesson arrays to respect cognitive capacity.
- An in-memory deterministic sanitizer validates roadmap JSON to prevent LLM schema drift without recursive API repair costs.

### 2. Hybrid RAG (Retrieval-Augmented Generation)
- Supports PDF, TXT, and Markdown files up to 25MB.
- Uses `all-MiniLM-L6-v2` dense vectors (384 dimensions) combined with PostgreSQL Full-Text Search `to_tsvector('english', content)`.
- Fuses results via Reciprocal Rank Fusion:
  $$RRF\_Score(d) = \sum_{m \in \{dense, fts\}} \frac{1}{60 + rank_m(d)}$$
- Dual modes: Mode A (grounded directly on uploaded chunks) and Mode B (generative synthesis when no notes exist).

### 3. Persistent Learning Cycle State Machine
- Finite state progression: `pending` → `lesson_gen` → `doubt` → `quiz_gen` → `eval` → `adaptive` → `completed`.
- Stored persistently in PostgreSQL `cycle_runs`.
- Disconnect resumption: If a user closes the tab or loses internet connection, reopening the session restores the exact step and cached outputs without re-running LLM prompts.

### 4. Local Neural Voice Pipeline
- Synthesizes 24kHz mono 16-bit PCM WAV audio using Kokoro-82M ONNX model locally.
- Latency strictly capped under 200ms (achieves 55ms benchmark value).
- Integrates Groq `whisper-large-v3-turbo` for voice doubt recording and verbal input.

### 5. Formative Assessment & Adaptive Replanning
- 4-item quiz: 3 Multiple Choice Questions + 1 Short Answer Conceptual Question.
- Anti-cheating guard: Answers and rubrics are excluded from student-facing payloads until submission.
- Deterministic exact-match scoring for MCQs; structured rubric scoring for short answer.
- Triggers `AdaptiveAgent` when total score is $< 70\%$, generating a prerequisite review module and taking an audit snapshot in `roadmap_versions`.

### 6. Wilson Score Community Library
- Community notes scored via 95% Wilson confidence lower bound ($z=1.96$):
  $$W = \frac{\hat{p} + \frac{z^2}{2n} - z \sqrt{\frac{\hat{p}(1-\hat{p}) + \frac{z^2}{4n}}{n}}}{1 + \frac{z^2}{n}}$$
- Deep Clone Decoupling: Imported notes create isolated copies of text and embeddings in the importer's workspace. Deleting the source note does not break student clones.
- Automated Moderation: Notes receiving $\ge 3$ reports are automatically hidden from the public feed.

## States and Boundaries
- **First Use**: Empty dashboard prompting the user to declare their first learning goal.
- **Normal Use**: Dashboard displaying current active sprint, next scheduled session, and roadmap progress.
- **Error States**: Clear fallback banners when external API limits are reached; local TTS and retrieval continue functioning offline.
- **Persistence**: All user goals, roadmaps, notes, vector embeddings, cycle states, quiz scores, and schedules persist indefinitely in PostgreSQL 16.
- **Permissions & Security**: Strict tenant isolation enforced at SQL query level (`user_id` foreign keys and token verification). Private notes are never accessible by other users.

## Product Decisions
- **Deterministic State Machine vs Autonomous Chat**: Chosen to eliminate unpredictability, preserve pedagogical structure, and enable reliable multi-session resumption.
- **Local Neural ONNX vs Cloud Voice API**: Chosen to eliminate recurring voice API billing, prevent user data leakage, and achieve ultra-low 55ms synthesis latency.
- **Reciprocal Rank Fusion ($k=60$)**: Chosen because combining dense semantic search with keyword search prevents missing exact code symbols, acronyms, or theorem names.

## What We're Building
The complete, end-to-end verified proof-of-concept comprising the FastAPI backend, PostgreSQL + pgvector storage, local ONNX engines, Groq LLM integration, and React/Tailwind frontend.

## Deferred From the POC
- Paid subscription and credit billing.
- Real-time WebRTC collaborative study sessions.
- Mobile native application wrapper.

## Possible Later Enhancements
- Fine-tuned local SLM (e.g. Qwen2.5-Coder-7B) for completely offline air-gapped operation.
- Automated code execution sandbox inside the lesson modal.

## Non-Goals
- Building an open-ended generic AI chat assistant.
- Scraper bots that crawl unverified web articles.
- High-frequency social media feeds.

## Open Questions
- None. All architectural decisions and state invariants are validated with 19/19 passing regression tests.
