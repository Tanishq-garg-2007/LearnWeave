---
doc: scope
status: approved
---

# LearnWeave AI

An agentic, personalized, and cost-controlled learning platform that structures curriculum into 2-week active sprint roadmaps, delivers dual-mode grounded lessons, resolves doubts via sub-60ms local neural voice, and dynamically adapts roadmaps based on formative assessment scores.

## The Unique Kernel
A deterministic, persistent 6-step learning state machine (`pending` → `lesson_gen` → `doubt` → `quiz_gen` → `eval` → `adaptive` → `completed`) combined with **Cognitive Budget Pacing** (enforcing detailed lessons strictly for Weeks 1 and 2, while dynamically locking future weeks as placeholder modules). Instead of generic LLM conversations with high latency and prompt drift, it guarantees zero-loss session recovery across disconnects, local ONNX neural voice in 55ms, and automatic curriculum remediation whenever assessment scores drop below 70%.

## Who It's For
Self-directed university students, bootcamp developers, and technical learners who currently struggle with "tutorial hell," fragmented YouTube playlists, or chaotic, un-grounded ChatGPT chat histories. They want an organized curriculum that adapts to their uploaded lecture notes and actively verifies their conceptual mastery before letting them move ahead.

## The Core Loop
1. The student logs into their private workspace and inputs a learning target (e.g., "Full-Stack FastAPI & Vector Databases").
2. The platform generates an active 2-week sprint roadmap with actionable, structured lessons and locked future placeholders.
3. The student opens an interactive lesson, powered either by their uploaded notes (Mode A: Hybrid RAG) or synthesized AI curriculum (Mode B).
4. The student listens via local neural voice (Kokoro-82M), asks clarifying doubts verbally or via text, and immediately attempts a formative 4-question assessment.
5. The evaluation agent scores the quiz; if mastery is below 70%, an automated adaptive review lesson is inserted into their sprint before unlocking the next topic.

## Inspiration & Identity
- **Tone & Mood**: Deep, focused, and distraction-free. Slate-950 backdrop with vibrant indigo and emerald accents, crisp typography, and fluid micro-animations.
- **Pedagogical Influence**: The mastery learning model (Bloom's 2 Sigma Problem) augmented with structured agentic workflows and spaced repetition calendars (+3d, +7d).
- **Design References**: Minimalist modern developer consoles (Vercel, Linear, Raycast) paired with educational clarity (Khan Academy).

## Why This Matters to the Learner
AI should not merely answer one-off questions; it should act as an intentional, patient tutor that remembers previous progress, respects cognitive capacity, and holds the learner accountable through continuous formative feedback without cloud vendor lock-in.

## What "Working" Looks Like
A student creates a goal, generates a roadmap, uploads a lecture PDF, starts the learning cycle, listens to the lesson in natural 24kHz audio synthesized locally in 55ms, submits a doubt, completes a hybrid quiz (3 MCQs + 1 open-ended rubric question), and watches the platform adaptively schedule a spaced review session or remediation lesson in real time.

## The POC Boundary
- **In Scope**:
  - Secure JWT authentication and isolated multi-user workspaces.
  - Cognitive-budgeted 2-week sprint roadmap generation with deterministic schema sanitization.
  - Hybrid RAG document pipeline: PDF/MD/TXT semantic chunking, 384-d dense embeddings (`all-MiniLM-L6-v2`), pgvector cosine similarity, and PostgreSQL Full-Text Search fused via Reciprocal Rank Fusion ($k=60$).
  - Persistent 6-step state machine with disconnect resumption stored in `cycle_runs`.
  - Local neural TTS (Kokoro-82M ONNX) and Whisper STT doubt input.
  - Hybrid quiz generation and rubric-based evaluation agent with topic mastery profile tracking.
  - Dynamic adaptive replanning when quiz scores fall below 70%.
  - Spaced repetition calendar scheduling (+3 days, +7 days).
  - Community note publishing with Wilson score 95% confidence interval ranking and decoupled note cloning.
- **Later**:
  - Live bidirectional WebRTC audio conversational streaming.
  - Collaborative multiplayer study rooms.
  - Mobile native apps (React Native / Expo).

## Explicitly Cut
- **Recursive LLM Self-Healing Loops**: Replaced with deterministic in-memory schema validation and sanitizers to prevent expensive latency spikes and rate-limit exhaustion.
- **Cloud TTS Services (ElevenLabs/OpenAI TTS)**: Cut in favor of local ONNX Kokoro-82M to preserve student privacy, eliminate recurring API bills, and reduce synthesis latency to under 60ms.
- **Naive Chatbot Free-Form Dialogue**: Cut in favor of an explicit 6-step finite state machine to prevent conversation context rot and unbounded token consumption.
