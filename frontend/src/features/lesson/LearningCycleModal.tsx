import React, { useState, useEffect, useRef } from "react";
import {
  X,
  Sparkles,
  BookOpen,
  Volume2,
  Mic,
  MicOff,
  HelpCircle,
  Award,
  Send,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  Pause,
  ArrowRight,
  Layers,
  RotateCw,
  FileText,
} from "lucide-react";
import { api } from "@/api";
import type { LessonResponse, NormalizedQuiz, QuizSubmitResponse } from "@/api/types";
import { useToast } from "@/components/ui/Toast";

interface LearningCycleModalProps {
  lesson: LessonResponse | null;
  isOpen: boolean;
  onClose: () => void;
  onLessonCompleted?: () => void;
}

type StepKey = "content" | "voice" | "doubts" | "quiz" | "eval" | "adaptive";

export function LearningCycleModal({
  lesson,
  isOpen,
  onClose,
  onLessonCompleted,
}: LearningCycleModalProps): JSX.Element | null {
  const [activeStep, setActiveStep] = useState<StepKey>("content");
  const [isLoading, setIsLoading] = useState(false);
  const [lessonData, setLessonData] = useState<any>(null);

  // Audio state
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [voiceSpeed, setVoiceSpeed] = useState<number>(1);
  const [isSynthesizingVoice, setIsSynthesizingVoice] = useState(false);
  const [selectedVoice, setSelectedVoice] = useState<string>("af_heart");
  const [audioEngine, setAudioEngine] = useState<string>("kokoro-82m");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Doubts state
  const [doubts, setDoubts] = useState<Array<{ q: string; a: string; citations?: string[] }>>([]);
  const [doubtInput, setDoubtInput] = useState("");
  const [isAskingDoubt, setIsAskingDoubt] = useState(false);
  const [isRecordingVoice, setIsRecordingVoice] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Quiz state
  const [quizData, setQuizData] = useState<NormalizedQuiz | null>(null);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, string>>({});
  const [shortAnswer, setShortAnswer] = useState("");
  const [evalResult, setEvalResult] = useState<QuizSubmitResponse | null>(null);
  const [isSubmittingQuiz, setIsSubmittingQuiz] = useState(false);

  // Cycle state machine
  const [cycleId, setCycleId] = useState<string | null>(null);
  const [completedCycleSteps, setCompletedCycleSteps] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const toast = useToast();

  useEffect(() => {
    if (isOpen && lesson) {
      loadLessonAndCycle();
    } else {
      // Reset
      setLessonData(null);
      setAudioUrl(null);
      setIsPlayingAudio(false);
      setDoubts([]);
      setQuizData(null);
      setEvalResult(null);
      setCycleId(null);
      setActiveStep("content");
      setError(null);
    }
  }, [isOpen, lesson?.id]);

  const loadLessonAndCycle = async () => {
    if (!lesson) return;
    setIsLoading(true);
    setError(null);

    try {
      // 1. Get or generate lesson content
      let contentData: any = null;
      try {
        const fetched = await api.getLesson(lesson.id);
        const raw = fetched?.content || (fetched as any)?.lesson_content;
        if (raw?.sections && raw.sections.length > 0) {
          contentData = { ...fetched, content: raw };
        }
      } catch {
        // Not generated yet, proceed to generate
      }

      if (!contentData) {
        contentData = await api.generateLesson(lesson.id);
      }
      setLessonData(contentData);

      // 2. Start or resume persistent learning cycle
      try {
        const cycle = await api.startCycle(lesson.id);
        setCycleId(cycle.cycle_id);
        setCompletedCycleSteps(cycle.completed_steps || []);
      } catch (cErr) {
        console.warn("Cycle start fallback:", cErr);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load lesson content.");
    } finally {
      setIsLoading(false);
    }
  };

  // Helper to extract clean text for narration
  const getNarrationText = (): string => {
    const content = (lessonData as any)?.content || (lessonData as any)?.lesson_content || (lesson as any)?.content || (lesson as any)?.lesson_content;
    let text = "";
    if (typeof content?.summary === "string" && content.summary.trim()) {
      text = content.summary.trim();
    } else if (Array.isArray(content?.key_takeaways) && content.key_takeaways.length > 0) {
      text = content.key_takeaways.join(". ");
    } else if (Array.isArray(content?.sections) && content.sections.length > 0) {
      const first = content.sections[0];
      text = (first.content || first.explanation || first.heading || first.title || "").slice(0, 500);
    }
    if (!text.trim()) {
      text = `Welcome to this interactive lesson on ${lesson?.title || "your study topic"}. We will cover the essential principles, architecture, and step-by-step concepts.`;
    }
    return text;
  };

  // Synthesize voice audio via Kokoro TTS
  const handleSynthesizeVoice = async () => {
    setIsSynthesizingVoice(true);
    try {
      const summaryText = getNarrationText();
      const blob = await api.speak(summaryText, selectedVoice);
      if ((blob as any).engine) {
        setAudioEngine((blob as any).engine);
      }
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setActiveStep("voice");
      toast.success("Kokoro-82M neural speech narration generated!");
    } catch (err: any) {
      toast.error(err?.message || "Voice narration unavailable.");
    } finally {
      setIsSynthesizingVoice(false);
    }
  };

  const toggleAudio = () => {
    if (!audioRef.current) return;
    if (isPlayingAudio) {
      audioRef.current.pause();
      setIsPlayingAudio(false);
    } else {
      audioRef.current.playbackRate = voiceSpeed;
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => setIsPlayingAudio(true))
          .catch((err) => {
            console.warn("Audio play issue:", err);
            setIsPlayingAudio(false);
          });
      } else {
        setIsPlayingAudio(true);
      }
    }
  };

  // Speech recording for Whisper STT
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        setIsLoading(true);
        try {
          const res = await api.listen(audioBlob);
          if (res.transcription) {
            setDoubtInput(res.transcription);
            toast.success("Voice transcribed!");
          }
        } catch {
          toast.error("Failed to transcribe speech.");
        } finally {
          setIsLoading(false);
          stream.getTracks().forEach((track) => track.stop());
        }
      };

      mediaRecorder.start();
      setIsRecordingVoice(true);
    } catch {
      toast.error("Microphone access denied or unavailable.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecordingVoice) {
      mediaRecorderRef.current.stop();
      setIsRecordingVoice(false);
    }
  };

  // Submit Doubt to AI
  const handleAskDoubt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!doubtInput.trim() || !lesson) return;

    const question = doubtInput.trim();
    setDoubtInput("");
    setIsAskingDoubt(true);

    try {
      let answerText = "";
      let citations: string[] = [];

      if (cycleId) {
        try {
          const cycleRes = await api.submitCycleStep(cycleId, "doubt", { doubt: question });
          const doubtOutput = (cycleRes as any)?.step_outputs?.doubt || (cycleRes as any)?.context?.doubt;
          answerText = doubtOutput?.answer || doubtOutput || "Answer synthesized from notes.";
        } catch {
          const doubtRes = await api.askDoubt(lesson.id, question);
          answerText = doubtRes.answer;
          citations = doubtRes.resolved_citations || [];
        }
      } else {
        const doubtRes = await api.askDoubt(lesson.id, question);
        answerText = doubtRes.answer;
        citations = doubtRes.resolved_citations || [];
      }

      setDoubts((prev) => [...prev, { q: question, a: answerText, citations }]);
    } catch (err: any) {
      toast.error(err?.message || "Failed to resolve doubt.");
    } finally {
      setIsAskingDoubt(false);
    }
  };

  // Fetch or generate Quiz
  const handleStartQuiz = async () => {
    if (!lesson) return;
    setIsLoading(true);
    setError(null);

    try {
      const quiz = await api.generateQuiz(lesson.id);
      setQuizData(quiz);
      setMcqAnswers({});
      setShortAnswer("");
      setActiveStep("quiz");
    } catch (err: any) {
      setError(err?.message || "Failed to generate formative quiz.");
      toast.error(err?.message || "Failed to generate quiz.");
    } finally {
      setIsLoading(false);
    }
  };

  // Submit Quiz Answers
  const handleSubmitQuiz = async () => {
    if (!lesson || !quizData) return;

    setIsSubmittingQuiz(true);
    setError(null);

    try {
      const answersPayload = quizData.questions.map((q) => {
        if (q.question_type === "conceptual_open_ended" || !q.options) {
          return {
            question_index: q.question_index,
            written_answer: shortAnswer.trim() || "No answer provided",
          };
        }
        const selected = mcqAnswers[String(q.question_index)];
        // An unanswered MCQ goes without an option, so the server grades it as wrong.
        // Never default to a letter: that credits "A" for a question the student skipped.
        return {
          question_index: q.question_index,
          ...(selected ? { selected_option: selected } : {}),
        };
      });

      const res = await api.submitQuiz(lesson.id, quizData.quiz_id, answersPayload);
      setEvalResult(res);

      if (res.passed) {
        // Mark lesson completed
        try {
          await api.updateLessonStatus(lesson.id, "completed");
          if (onLessonCompleted) onLessonCompleted();
        } catch (statusErr) {
          console.warn("Status update error:", statusErr);
        }
      }

      // Check if adaptive remediation is triggered
      if (res.score_percentage < 70) {
        setActiveStep("adaptive");
      } else {
        setActiveStep("eval");
      }
    } catch (err: any) {
      setError(err?.message || "Quiz evaluation failed.");
      toast.error(err?.message || "Quiz evaluation failed.");
    } finally {
      setIsSubmittingQuiz(false);
    }
  };

  if (!isOpen || !lesson) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/40 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl bg-white/95 border border-white/90 shadow-2xl rounded-3xl flex flex-col max-h-[92vh] overflow-hidden">
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between bg-white/60 backdrop-blur-md">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-[#252229] flex items-center justify-center text-white shadow-soft p-1.5">
              <img
                src="/favicon-white-96x96.png"
                alt="LearnWeave Favicon"
                className="w-5 h-5 object-contain"
              />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-cyan-100 text-cyan-800">
                  Adaptive Learning Cycle
                </span>
                <span className="text-xs text-muted font-medium">
                  {lesson.duration_minutes} min • {lesson.status}
                </span>
              </div>
              <h2 className="text-base sm:text-lg font-bold text-ink leading-tight">
                {lesson.title}
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-muted hover:text-ink p-1.5 rounded-full hover:bg-black/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Navigation Bar */}
        <div className="px-6 py-2.5 border-b border-surface-border bg-[#FAF7F3] flex items-center gap-2 overflow-x-auto text-xs font-semibold">
          <button
            onClick={() => setActiveStep("content")}
            className={`px-3.5 py-1.5 rounded-full transition-all flex items-center gap-1.5 ${
              activeStep === "content"
                ? "bg-[#252229] text-white shadow-sm"
                : "text-muted hover:text-ink hover:bg-black/5"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>1. Lesson Content</span>
          </button>

          <button
            onClick={() => {
              setActiveStep("voice");
              if (!audioUrl && !isSynthesizingVoice) {
                handleSynthesizeVoice();
              }
            }}
            className={`px-3.5 py-1.5 rounded-full transition-all flex items-center gap-1.5 ${
              activeStep === "voice"
                ? "bg-[#252229] text-white shadow-sm"
                : "text-muted hover:text-ink hover:bg-black/5"
            }`}
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>2. Voice Narration</span>
          </button>

          <button
            onClick={() => setActiveStep("doubts")}
            className={`px-3.5 py-1.5 rounded-full transition-all flex items-center gap-1.5 ${
              activeStep === "doubts"
                ? "bg-[#252229] text-white shadow-sm"
                : "text-muted hover:text-ink hover:bg-black/5"
            }`}
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>3. Ask AI Doubt</span>
          </button>

          <button
            onClick={quizData ? () => setActiveStep("quiz") : handleStartQuiz}
            className={`px-3.5 py-1.5 rounded-full transition-all flex items-center gap-1.5 ${
              activeStep === "quiz"
                ? "bg-[#252229] text-white shadow-sm"
                : "text-muted hover:text-ink hover:bg-black/5"
            }`}
          >
            <Award className="w-3.5 h-3.5" />
            <span>4. Knowledge Quiz</span>
          </button>

          {evalResult && (
            <button
              onClick={() => setActiveStep("eval")}
              className={`px-3.5 py-1.5 rounded-full transition-all flex items-center gap-1.5 ${
                activeStep === "eval"
                  ? "bg-[#252229] text-white shadow-sm"
                  : "text-muted hover:text-ink hover:bg-black/5"
              }`}
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              <span>5. Evaluation ({evalResult.score_percentage}%)</span>
            </button>
          )}

          {evalResult && evalResult.score_percentage < 70 && (
            <button
              onClick={() => setActiveStep("adaptive")}
              className={`px-3.5 py-1.5 rounded-full transition-all flex items-center gap-1.5 ${
                activeStep === "adaptive"
                  ? "bg-amber-600 text-white shadow-sm"
                  : "text-amber-700 bg-amber-50 hover:bg-amber-100"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>6. Remediation</span>
            </button>
          )}
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3.5 rounded-2xl bg-danger/10 border border-danger/20 text-xs text-danger font-medium flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3 text-center">
              <div className="h-10 w-10 rounded-full border-3 border-ink/20 border-t-ink animate-spin" />
              <p className="text-xs font-semibold text-ink">
                Generating educational content grounded in your materials...
              </p>
            </div>
          ) : (
            <>
              {/* STEP 1: LESSON CONTENT */}
              {activeStep === "content" && (
                <div className="space-y-6">
                  {lessonData?.content?.grounding_type && (
                    <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-cyan-50 border border-cyan-200 text-[11px] font-semibold text-cyan-900">
                      <FileText className="w-3.5 h-3.5 text-cyan-600" />
                      <span>
                        Grounded via {lessonData.content.grounding_type === "rag_grounded" ? "RAG Knowledge Base & Notes" : "AI Learning Service"}
                      </span>
                    </div>
                  )}

                  {(lessonData?.content?.sections || lessonData?.lesson_content?.sections)?.map((sec: any, idx: number) => (
                    <div
                      key={idx}
                      className="p-5 rounded-2xl bg-white border border-surface-border shadow-sm space-y-2 text-left"
                    >
                      <h3 className="text-sm font-bold text-ink flex items-center gap-2">
                        <span className="w-5 h-5 rounded-md bg-black/5 text-[10px] flex items-center justify-center font-mono">
                          {idx + 1}
                        </span>
                        {sec.title || sec.heading || `Section ${idx + 1}`}
                      </h3>
                      <div className="text-xs text-text/80 leading-relaxed whitespace-pre-line pl-7">
                        {sec.explanation || sec.content}
                      </div>

                      {sec.cited_chunk_ids && sec.cited_chunk_ids.length > 0 && (
                        <div className="pl-7 pt-2 flex items-center gap-1.5 text-[10px] text-muted">
                          <span className="font-semibold">Citations:</span>
                          {sec.cited_chunk_ids.map((cid: string) => (
                            <span
                              key={cid}
                              className="px-1.5 py-0.5 rounded bg-black/5 font-mono text-[9px]"
                            >
                              chunk-{cid.slice(0, 6)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}

                  {lessonData?.content?.key_takeaways?.length > 0 && (
                    <div className="p-5 rounded-2xl bg-[#F6F1EA] border border-surface-border text-left space-y-2">
                      <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                        Key Takeaways
                      </h4>
                      <ul className="space-y-1.5 text-xs text-text/80 list-disc list-inside">
                        {lessonData.content.key_takeaways.map((point: string, i: number) => (
                          <li key={i}>{point}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Bottom Action Controls */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-surface-border">
                    <button
                      onClick={handleSynthesizeVoice}
                      disabled={isSynthesizingVoice}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-white hover:bg-black/5 border border-surface-border text-xs font-semibold text-ink transition-colors shadow-sm disabled:opacity-50"
                    >
                      {isSynthesizingVoice ? (
                        <>
                          <RotateCw className="w-4 h-4 animate-spin text-cyan-600" />
                          <span>Synthesizing Voice...</span>
                        </>
                      ) : (
                        <>
                          <Volume2 className="w-4 h-4 text-cyan-700" />
                          <span>Synthesize Voice Narration</span>
                        </>
                      )}
                    </button>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setActiveStep("doubts")}
                        className="px-4 py-2.5 rounded-full bg-black/5 hover:bg-black/10 text-xs font-semibold text-ink transition-colors"
                      >
                        Ask a Doubt
                      </button>
                      <button
                        onClick={handleStartQuiz}
                        className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md transition-all active:scale-95"
                      >
                        <span>Take Knowledge Quiz</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2: VOICE AUDIO NARRATION */}
              {activeStep === "voice" && (
                <div className="p-8 rounded-3xl bg-white border border-surface-border shadow-sm text-center space-y-6 max-w-lg mx-auto">
                  <div className="w-16 h-16 rounded-full bg-cyan-100 text-cyan-800 flex items-center justify-center mx-auto shadow-inner">
                    <Volume2 className="w-8 h-8" />
                  </div>
                  <div>
                    <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-50 border border-cyan-200 text-[11px] font-semibold text-cyan-900 mb-2">
                      <Sparkles className="w-3.5 h-3.5 text-cyan-600" />
                      <span>{audioEngine === "kokoro-82m" ? "⚡ Kokoro-82M Neural Model (24kHz Mono WAV)" : "Standard Synthesizer (24kHz WAV)"}</span>
                    </div>
                    <h3 className="text-lg font-bold text-ink">Neural Voice Narration</h3>
                    <p className="text-xs text-muted mt-1 max-w-md mx-auto line-clamp-2">
                      Listen to an articulate, synthesized spoken explanation of {lesson.title}
                    </p>
                  </div>

                  {/* Voice Selector */}
                  <div className="flex flex-col sm:flex-row items-center justify-center gap-2 text-xs">
                    <label className="text-muted font-medium">Select Voice:</label>
                    <select
                      value={selectedVoice}
                      onChange={(e) => setSelectedVoice(e.target.value)}
                      disabled={isSynthesizingVoice}
                      className="px-3 py-1.5 rounded-xl border border-surface-border bg-white text-ink text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-focus shadow-xs"
                    >
                      <option value="af_heart">Heart (Warm, Expressive · Female)</option>
                      <option value="af_bella">Bella (Clear, Articulate · Female)</option>
                      <option value="af_nicole">Nicole (Dynamic · Female)</option>
                      <option value="am_adam">Adam (Conversational · Male)</option>
                      <option value="am_michael">Michael (Engaging · Male)</option>
                      <option value="bf_emma">Emma (British Accent · Female)</option>
                      <option value="bm_george">George (Academic · Male)</option>
                    </select>
                  </div>

                  {/* Narration Preview snippet */}
                  <div className="p-3.5 rounded-2xl bg-[#F6F1EA] border border-surface-border text-left">
                    <p className="text-[10px] font-bold text-muted uppercase tracking-wider mb-1">Narration Script</p>
                    <p className="text-xs text-text/80 line-clamp-3 leading-relaxed italic">
                      "{getNarrationText()}"
                    </p>
                  </div>

                  {audioUrl && (
                    <audio
                      ref={audioRef}
                      src={audioUrl}
                      onPlay={() => setIsPlayingAudio(true)}
                      onPause={() => setIsPlayingAudio(false)}
                      onEnded={() => setIsPlayingAudio(false)}
                      className="w-full mt-2"
                      controls
                    />
                  )}

                  {/* Action Controls */}
                  <div className="flex flex-wrap items-center justify-center gap-3">
                    {isSynthesizingVoice ? (
                      <div className="flex items-center gap-2.5 px-6 py-3 rounded-full bg-cyan-100 text-cyan-900 text-xs font-semibold animate-pulse shadow-sm">
                        <RotateCw className="w-4 h-4 animate-spin text-cyan-700" />
                        <span>Kokoro-82M is synthesizing neural audio...</span>
                      </div>
                    ) : !audioUrl ? (
                      <button
                        onClick={handleSynthesizeVoice}
                        className="inline-flex items-center gap-2 px-7 py-3 rounded-full bg-[#252229] hover:bg-[#151318] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
                      >
                        <Volume2 className="w-4 h-4 text-cyan-300" />
                        <span>Generate Kokoro Narration</span>
                      </button>
                    ) : (
                      <>
                        <button
                          onClick={toggleAudio}
                          className="h-14 w-14 rounded-full bg-[#252229] hover:bg-[#151318] text-white flex items-center justify-center shadow-lg transition-transform active:scale-95"
                          title={isPlayingAudio ? "Pause Audio" : "Play Audio"}
                        >
                          {isPlayingAudio ? (
                            <Pause className="w-6 h-6" />
                          ) : (
                            <Play className="w-6 h-6 ml-1" />
                          )}
                        </button>
                        <button
                          onClick={handleSynthesizeVoice}
                          disabled={isSynthesizingVoice}
                          className="px-4 py-2 rounded-full border border-surface-border bg-white hover:bg-black/5 text-xs font-semibold text-ink transition-colors shadow-xs"
                        >
                          Regenerate Voice
                        </button>
                      </>
                    )}
                  </div>

                  {audioUrl && (
                    <div className="flex items-center justify-center gap-2 text-xs">
                      <span className="text-muted font-medium">Speed:</span>
                      {[0.75, 1, 1.25, 1.5].map((speed) => (
                        <button
                          key={speed}
                          onClick={() => {
                            setVoiceSpeed(speed);
                            if (audioRef.current) audioRef.current.playbackRate = speed;
                          }}
                          className={`px-2.5 py-1 rounded-lg font-mono text-[11px] font-semibold transition-colors ${
                            voiceSpeed === speed
                              ? "bg-[#252229] text-white"
                              : "bg-black/5 text-muted hover:text-ink"
                          }`}
                        >
                          {speed}x
                        </button>
                      ))}
                    </div>
                  )}

                  <div className="pt-4 border-t border-surface-border flex items-center justify-between gap-3">
                    <button
                      onClick={() => setActiveStep("content")}
                      className="px-4 py-2 rounded-full bg-black/5 hover:bg-black/10 text-xs font-semibold text-ink transition-colors"
                    >
                      Back to Content
                    </button>
                    <button
                      onClick={() => setActiveStep("doubts")}
                      className="px-6 py-2.5 rounded-full bg-[#252229] text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
                    >
                      Proceed to Doubt Resolution
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 3: DOUBTS RESOLUTION */}
              {activeStep === "doubts" && (
                <div className="space-y-6 text-left">
                  <div className="p-4 rounded-2xl bg-cyan-50/70 border border-cyan-200 text-xs text-cyan-900 leading-relaxed">
                    Have any questions regarding this lesson? Ask directly below. Answers are verified
                    and grounded against your uploaded study notes.
                  </div>

                  {/* Doubt Conversation History */}
                  <div className="space-y-4">
                    {doubts.map((item, idx) => (
                      <div key={idx} className="space-y-2">
                        <div className="flex justify-end">
                          <div className="max-w-[80%] px-4 py-2.5 rounded-2xl bg-[#252229] text-white text-xs leading-relaxed">
                            {item.q}
                          </div>
                        </div>
                        <div className="flex justify-start">
                          <div className="max-w-[85%] px-5 py-3.5 rounded-2xl bg-white border border-surface-border shadow-sm text-xs text-text leading-relaxed space-y-1.5">
                            <div className="flex items-center gap-1.5 text-[10px] font-bold text-violet">
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>AI Tutor Explanation</span>
                            </div>
                            <p>{item.a}</p>
                            {item.citations && item.citations.length > 0 && (
                              <div className="pt-1 text-[10px] text-muted">
                                Source chunks: {item.citations.join(", ")}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Ask Form with Text & Speech-to-Text */}
                  <form onSubmit={handleAskDoubt} className="pt-2 flex items-center gap-2">
                    <input
                      type="text"
                      value={doubtInput}
                      onChange={(e) => setDoubtInput(e.target.value)}
                      placeholder="Type your question or use speech input..."
                      disabled={isAskingDoubt}
                      className="flex-1 px-4 py-3 rounded-2xl bg-white border border-surface-border text-xs text-ink placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-focus"
                    />

                    {/* Microphone STT button */}
                    <button
                      type="button"
                      onClick={isRecordingVoice ? stopRecording : startRecording}
                      className={`h-11 w-11 rounded-2xl flex items-center justify-center transition-colors shadow-sm ${
                        isRecordingVoice
                          ? "bg-red-500 text-white animate-pulse"
                          : "bg-white border border-surface-border text-muted hover:text-ink"
                      }`}
                      title={isRecordingVoice ? "Stop Recording" : "Voice Input (Whisper STT)"}
                    >
                      {isRecordingVoice ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                    </button>

                    <button
                      type="submit"
                      disabled={isAskingDoubt || !doubtInput.trim()}
                      className="px-5 py-3 rounded-2xl bg-[#252229] hover:bg-[#151318] disabled:opacity-50 text-white text-xs font-semibold shadow-md flex items-center gap-2"
                    >
                      {isAskingDoubt ? (
                        <RotateCw className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </button>
                  </form>

                  <div className="pt-4 flex justify-end">
                    <button
                      type="button"
                      onClick={handleStartQuiz}
                      className="inline-flex items-center gap-1.5 px-6 py-2.5 rounded-full bg-[#252229] text-white text-xs font-semibold shadow-md"
                    >
                      <span>Proceed to Quiz</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 4: KNOWLEDGE QUIZ */}
              {activeStep === "quiz" && quizData && (
                <div className="space-y-6 text-left">
                  <div className="p-4 rounded-2xl bg-white border border-surface-border flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-ink">{quizData.title}</h3>
                      <p className="text-xs text-muted">
                        3 Multiple Choice Questions + 1 Conceptual Short Answer
                      </p>
                    </div>
                    <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded-full bg-cyan-100 text-cyan-800">
                      Assessment
                    </span>
                  </div>

                  <div className="space-y-6">
                    {quizData.questions.map((q, idx) => (
                      <div
                        key={idx}
                        className="p-5 rounded-2xl bg-white border border-surface-border shadow-sm space-y-3"
                      >
                        <div className="flex items-baseline gap-2">
                          <span className="w-5 h-5 rounded-full bg-black/5 text-[10px] font-bold flex items-center justify-center font-mono">
                            {idx + 1}
                          </span>
                          <p className="text-xs font-bold text-ink leading-relaxed">{q.prompt}</p>
                        </div>

                        {/* MCQ Options */}
                        {q.options && q.option_keys && (
                          <div className="grid grid-cols-1 gap-2 pl-7">
                            {q.options.map((optText, oIdx) => {
                              const letter = q.option_keys![oIdx] || String.fromCharCode(65 + oIdx);
                              const isSelected = mcqAnswers[String(q.question_index)] === letter;

                              return (
                                <button
                                  key={letter}
                                  type="button"
                                  onClick={() =>
                                    setMcqAnswers((prev) => ({
                                      ...prev,
                                      [String(q.question_index)]: letter,
                                    }))
                                  }
                                  className={`p-3 rounded-xl border text-left text-xs transition-all flex items-center gap-3 ${
                                    isSelected
                                      ? "bg-cyan-50/80 border-cyan-400 text-cyan-950 font-semibold"
                                      : "bg-[#FAF7F4] border-surface-border text-text hover:bg-black/5"
                                  }`}
                                >
                                  <span
                                    className={`w-6 h-6 rounded-lg text-[10px] font-bold flex items-center justify-center font-mono ${
                                      isSelected
                                        ? "bg-cyan-600 text-white"
                                        : "bg-black/10 text-muted"
                                    }`}
                                  >
                                    {letter}
                                  </span>
                                  <span>{optText}</span>
                                </button>
                              );
                            })}
                          </div>
                        )}

                        {/* Open-ended Conceptual Question */}
                        {(!q.options || q.question_type === "conceptual_open_ended") && (
                          <div className="pl-7 space-y-1.5">
                            <textarea
                              rows={3}
                              value={shortAnswer}
                              onChange={(e) => setShortAnswer(e.target.value)}
                              placeholder="Explain clearly in 2-3 sentences based on the lesson concepts..."
                              className="w-full p-3 rounded-xl bg-[#FAF7F4] border border-surface-border text-xs text-ink placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-focus"
                            />
                            {q.rubric_criteria && (
                              <p className="text-[10px] text-muted">
                                Evaluated on: {q.rubric_criteria}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>

                  {/* Submit Quiz Button */}
                  <div className="pt-4 flex items-center justify-end">
                    <button
                      type="button"
                      onClick={handleSubmitQuiz}
                      disabled={isSubmittingQuiz}
                      className="inline-flex items-center gap-2 px-8 py-3 rounded-full bg-[#252229] hover:bg-[#151318] disabled:opacity-50 text-white text-xs font-semibold shadow-md active:scale-95 transition-all"
                    >
                      {isSubmittingQuiz ? (
                        <>
                          <RotateCw className="w-4 h-4 animate-spin" />
                          <span>Evaluating Answers via Rubric AI...</span>
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                          <span>Submit Assessment for Grading</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 5: EVALUATION RESULTS */}
              {activeStep === "eval" && evalResult && (
                <div className="space-y-6 text-left">
                  <div
                    className={`p-6 rounded-3xl border flex flex-col sm:flex-row items-center justify-between gap-4 ${
                      evalResult.passed
                        ? "bg-emerald-50/80 border-emerald-200"
                        : "bg-rose-50/80 border-rose-200"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-12 h-12 rounded-2xl flex items-center justify-center text-white shadow-soft ${
                          evalResult.passed ? "bg-emerald-600" : "bg-rose-600"
                        }`}
                      >
                        {evalResult.passed ? (
                          <CheckCircle2 className="w-6 h-6" />
                        ) : (
                          <XCircle className="w-6 h-6" />
                        )}
                      </div>
                      <div>
                        <h3 className="text-base font-bold text-ink">
                          {evalResult.passed ? "Assessment Passed!" : "Needs Revision"}
                        </h3>
                        <p className="text-xs text-muted">
                          {evalResult.feedback_summary ||
                            (evalResult.passed
                              ? "Congratulations! You have demonstrated concept mastery."
                              : "Score below 70%. Targeted revision is recommended.")}
                        </p>
                      </div>
                    </div>

                    <div className="text-right">
                      <p className="text-3xl font-display font-bold text-ink font-mono">
                        {evalResult.score_percentage}%
                      </p>
                      <p className="text-[10px] text-muted">Overall Score</p>
                    </div>
                  </div>

                  {/* Question-by-question breakdown */}
                  <div className="space-y-3">
                    <h4 className="text-xs font-bold text-ink uppercase tracking-wider">
                      Feedback Breakdown
                    </h4>
                    {evalResult.evaluations?.map((ev, i) => (
                      <div
                        key={i}
                        className="p-4 rounded-2xl bg-white border border-surface-border text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-ink">Question {ev.question_index}</span>
                          <span
                            className={`font-mono font-bold text-[11px] ${
                              ev.correct ? "text-emerald-600" : "text-rose-600"
                            }`}
                          >
                            Score: {ev.score} / {ev.max_score}
                          </span>
                        </div>
                        <p className="text-muted text-[11px] leading-relaxed">{ev.feedback}</p>
                      </div>
                    ))}
                  </div>

                  <div className="pt-4 flex items-center justify-end gap-3">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-6 py-2.5 rounded-full bg-[#252229] text-white text-xs font-semibold shadow-md"
                    >
                      Close & Return to Roadmap
                    </button>
                  </div>
                </div>
              )}

              {/* STEP 6: ADAPTIVE REMEDIATION */}
              {activeStep === "adaptive" && evalResult && (
                <div className="p-8 rounded-3xl bg-amber-50/70 border border-amber-200 text-left space-y-5">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-amber-600 text-white flex items-center justify-center shadow-soft">
                      <AlertTriangle className="w-6 h-6" />
                    </div>
                    <div>
                      <h3 className="text-base font-bold text-ink">
                        Targeted Revision Recommended
                      </h3>
                      <p className="text-xs text-muted">
                        Score was {evalResult.score_percentage}%. The AdaptiveRemediationAgent has
                        introduced targeted revision to reinforce the prerequisite concepts.
                      </p>
                    </div>
                  </div>

                  <div className="p-4 rounded-2xl bg-white border border-amber-200/80 text-xs text-text space-y-2">
                    <p className="font-semibold text-ink">Recommended Strategy:</p>
                    <p className="text-muted text-[11px] leading-relaxed">
                      1. Re-read the key sections in Lesson Content.
                      <br />
                      2. Submit any specific ambiguities to the Doubt Resolution agent.
                      <br />
                      3. A spaced repetition review session will be added to your study schedule.
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <button
                      type="button"
                      onClick={() => setActiveStep("content")}
                      className="px-5 py-2.5 rounded-full bg-white border border-surface-border text-xs font-semibold text-ink shadow-sm"
                    >
                      Review Content Again
                    </button>
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-6 py-2.5 rounded-full bg-[#252229] text-white text-xs font-semibold shadow-md"
                    >
                      Return to Roadmap
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default LearningCycleModal;
