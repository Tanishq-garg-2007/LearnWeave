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
  Layers
} from "lucide-react";
import { api, Lesson } from "../api/client";

interface LearningCycleModalProps {
  lesson: Lesson | null;
  isOpen: boolean;
  onClose: () => void;
  onLessonCompleted: () => void;
}

export const LearningCycleModal: React.FC<LearningCycleModalProps> = ({
  lesson,
  isOpen,
  onClose,
  onLessonCompleted,
}) => {
  const [activeStep, setActiveStep] = useState<"content" | "voice" | "doubts" | "quiz" | "eval">("content");
  const [isLoading, setIsLoading] = useState(false);
  const [lessonData, setLessonData] = useState<any>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Doubts state
  const [doubts, setDoubts] = useState<Array<{ q: string; a: string }>>([]);
  const [doubtInput, setDoubtInput] = useState("");
  const [isAskingDoubt, setIsAskingDoubt] = useState(false);
  const [isRecordingVoice, setIsRecordingVoice] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Quiz state
  const [quizData, setQuizData] = useState<any>(null);
  const [mcqAnswers, setMcqAnswers] = useState<Record<string, string>>({});
  const [shortAnswer, setShortAnswer] = useState("");
  const [evalResult, setEvalResult] = useState<any>(null);
  const [isSubmittingQuiz, setIsSubmittingQuiz] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && lesson) {
      loadLessonContent();
    } else {
      // Reset state on close
      setLessonData(null);
      setAudioUrl(null);
      setDoubts([]);
      setQuizData(null);
      setEvalResult(null);
      setActiveStep("content");
      setError(null);
    }
  }, [isOpen, lesson?.id]);

  const loadLessonContent = async () => {
    if (!lesson) return;
    setIsLoading(true);
    setError(null);
    try {
      // Try fetching first, or generate if not ready
      let data = await api.getLesson(lesson.id).catch(() => null);
      if (!data || !data.content || !data.content.sections) {
        data = await api.generateLesson(lesson.id);
      }
      setLessonData(data);
    } catch (err: any) {
      setError(err.message || "Failed to load lesson content");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSynthesizeVoice = async () => {
    if (!lessonData?.content) return;
    setIsLoading(true);
    try {
      const summaryText =
        lessonData.content.summary ||
        lessonData.content.sections?.[0]?.explanation ||
        `Lesson on ${lesson?.title}`;
      const blob = await api.speak(summaryText);
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
      setActiveStep("voice");
    } catch (err: any) {
      setError(err.message || "TTS Voice generation failed");
    } finally {
      setIsLoading(false);
    }
  };

  const handleAskDoubt = async (text?: string) => {
    const question = text || doubtInput;
    if (!question.trim() || !lesson) return;

    setIsAskingDoubt(true);
    try {
      const res = await api.askDoubt(lesson.id, question);
      setDoubts((prev) => [...prev, { q: question, a: res.answer }]);
      setDoubtInput("");
    } catch (err: any) {
      setError(err.message || "Failed to answer doubt");
    } finally {
      setIsAskingDoubt(false);
    }
  };

  const startVoiceRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        setIsAskingDoubt(true);
        try {
          const res = await api.listen(audioBlob);
          if (res.transcription) {
            await handleAskDoubt(res.transcription);
          }
        } catch (err: any) {
          setError("Speech recognition failed: " + err.message);
        } finally {
          setIsAskingDoubt(false);
        }
      };

      recorder.start();
      mediaRecorderRef.current = recorder;
      setIsRecordingVoice(true);
    } catch (err: any) {
      setError("Microphone access denied or unavailable: " + err.message);
    }
  };

  const stopVoiceRecording = () => {
    if (mediaRecorderRef.current && isRecordingVoice) {
      mediaRecorderRef.current.stop();
      setIsRecordingVoice(false);
    }
  };

  const handleLoadQuiz = async () => {
    if (!lesson) return;
    setIsLoading(true);
    try {
      const qz = await api.generateQuiz(lesson.id);
      setQuizData(qz);
      setActiveStep("quiz");
    } catch (err: any) {
      setError(err.message || "Failed to generate quiz");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitQuiz = async () => {
    if (!quizData) return;
    setIsSubmittingQuiz(true);
    setError(null);

    const answersPayload = quizData.questions.map((q: any) => ({
      question_id: q.id,
      answer_text: q.question_type === "mcq" ? mcqAnswers[q.id] || "" : shortAnswer,
    }));

    try {
      const result = await api.submitQuiz(quizData.quiz_id, answersPayload);
      setEvalResult(result);
      setActiveStep("eval");
      onLessonCompleted();
    } catch (err: any) {
      setError(err.message || "Failed to evaluate quiz");
    } finally {
      setIsSubmittingQuiz(false);
    }
  };

  if (!isOpen || !lesson) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Top Bar */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-bold text-xs">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-400">
                Interactive Learning Cycle
              </span>
              <h2 className="text-sm font-bold text-white truncate max-w-md">{lesson.title}</h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Navigation Tabs */}
        <div className="flex items-center border-b border-slate-800 bg-slate-900/40 px-6 gap-2 overflow-x-auto py-2">
          <button
            onClick={() => setActiveStep("content")}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeStep === "content"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>1. Lesson</span>
          </button>

          <button
            onClick={() => {
              if (!audioUrl) handleSynthesizeVoice();
              else setActiveStep("voice");
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeStep === "voice"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Volume2 className="w-3.5 h-3.5" />
            <span>2. Voice Audio</span>
          </button>

          <button
            onClick={() => setActiveStep("doubts")}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeStep === "doubts"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <HelpCircle className="w-3.5 h-3.5" />
            <span>3. Ask Doubts</span>
          </button>

          <button
            onClick={() => {
              if (!quizData) handleLoadQuiz();
              else setActiveStep("quiz");
            }}
            className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
              activeStep === "quiz" || activeStep === "eval"
                ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Award className="w-3.5 h-3.5" />
            <span>4. Quiz & Eval</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => setError(null)} className="font-bold underline">
                Dismiss
              </button>
            </div>
          )}

          {isLoading ? (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="w-8 h-8 border-3 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
              <p className="text-xs text-slate-400 mt-3">Synthesizing learning materials...</p>
            </div>
          ) : activeStep === "content" ? (
            /* Step 1: Lesson Content */
            <div className="space-y-6">
              {lessonData?.grounding_type === "rag_grounded" && (
                <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center gap-2 text-xs text-indigo-300">
                  <Sparkles className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                  <span>
                    Grounded in your private study notes with {lessonData.content.cited_chunks?.length || 0} citations.
                  </span>
                </div>
              )}

              {lessonData?.content?.summary && (
                <div className="p-4 rounded-xl bg-slate-850 border border-slate-800">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1">Lesson Overview</h4>
                  <p className="text-sm text-slate-200 leading-relaxed">{lessonData.content.summary}</p>
                </div>
              )}

              {lessonData?.content?.sections?.map((sec: any, idx: number) => (
                <div key={idx} className="space-y-2">
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <span className="text-indigo-400 font-mono text-sm">#{idx + 1}</span>
                    <span>{sec.title}</span>
                  </h3>
                  <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">{sec.explanation}</p>
                  {sec.key_takeaways && (
                    <div className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 space-y-1">
                      <span className="text-[10px] font-bold text-indigo-400 uppercase">Key Takeaways</span>
                      <ul className="list-disc list-inside text-xs text-slate-400 space-y-0.5">
                        {sec.key_takeaways.map((item: string, i: number) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}

              <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={handleSynthesizeVoice}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all hover:scale-105"
                >
                  <Volume2 className="w-4 h-4" />
                  <span>Listen via Kokoro TTS</span>
                </button>
              </div>
            </div>
          ) : activeStep === "voice" ? (
            /* Step 2: Voice Narration */
            <div className="space-y-6 text-center py-6">
              <div className="w-16 h-16 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mx-auto mb-2 shadow-xl shadow-indigo-600/20">
                <Volume2 className="w-8 h-8 text-indigo-400 animate-pulse" />
              </div>
              <h3 className="text-base font-bold text-white">Local Kokoro-82M Voice Synthesis</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                24kHz mono 16-bit PCM WAV generated with sub-second latency on your local workstation.
              </p>

              {audioUrl && (
                <div className="max-w-md mx-auto glass-panel p-4 rounded-2xl border border-slate-800">
                  <audio
                    ref={audioRef}
                    controls
                    src={audioUrl}
                    className="w-full"
                    autoPlay
                    onPlay={() => setIsPlayingAudio(true)}
                    onPause={() => setIsPlayingAudio(false)}
                  />
                </div>
              )}

              <div className="pt-6 flex items-center justify-center gap-3">
                <button
                  onClick={() => setActiveStep("doubts")}
                  className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs inline-flex items-center gap-2"
                >
                  <span>Ask a Doubt</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : activeStep === "doubts" ? (
            /* Step 3: Interactive Doubts */
            <div className="space-y-4">
              <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                {doubts.length === 0 ? (
                  <div className="p-8 text-center glass-panel rounded-2xl border border-slate-800">
                    <HelpCircle className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-xs text-slate-400">
                      Got stuck on a formula or concept? Ask your question by voice or text.
                    </p>
                  </div>
                ) : (
                  doubts.map((d, i) => (
                    <div key={i} className="space-y-2">
                      <div className="p-3 rounded-xl bg-indigo-950/30 border border-indigo-500/30 text-xs text-indigo-200">
                        <span className="font-bold">You: </span>
                        {d.q}
                      </div>
                      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 leading-relaxed whitespace-pre-line">
                        <span className="font-bold text-indigo-400">Tutor: </span>
                        {d.a}
                      </div>
                    </div>
                  ))
                )}
              </div>

              {/* Input Box */}
              <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Type your question or use the mic..."
                  value={doubtInput}
                  onChange={(e) => setDoubtInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleAskDoubt()}
                  disabled={isAskingDoubt}
                  className="flex-1 px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />

                {/* Voice Input Button */}
                <button
                  type="button"
                  onClick={isRecordingVoice ? stopVoiceRecording : startVoiceRecording}
                  className={`p-2.5 rounded-xl border transition-all ${
                    isRecordingVoice
                      ? "bg-rose-600 text-white border-rose-500 animate-pulse"
                      : "bg-slate-800 text-slate-300 border-slate-700 hover:text-white"
                  }`}
                  title={isRecordingVoice ? "Stop Recording & Transcribe" : "Hold to Speak via Groq Whisper"}
                >
                  {isRecordingVoice ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
                </button>

                <button
                  type="button"
                  onClick={() => handleAskDoubt()}
                  disabled={isAskingDoubt || !doubtInput.trim()}
                  className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send</span>
                </button>
              </div>

              <div className="pt-4 flex justify-end">
                <button
                  type="button"
                  onClick={handleLoadQuiz}
                  className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-2"
                >
                  <span>Take Assessment Quiz</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ) : activeStep === "quiz" ? (
            /* Step 4: Formative Quiz */
            <div className="space-y-6">
              {quizData?.questions?.map((q: any, idx: number) => (
                <div key={q.id} className="p-4 rounded-xl bg-slate-850 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                    <span>Question {idx + 1} of 4</span>
                    <span className="uppercase">{q.question_type}</span>
                  </div>
                  <h4 className="text-sm font-bold text-white">{q.prompt}</h4>

                  {q.question_type === "mcq" && q.options ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                      {q.options.map((opt: string, i: number) => {
                        const letter = ["A", "B", "C", "D"][i];
                        const isSelected = mcqAnswers[q.id] === letter;
                        return (
                          <button
                            key={i}
                            type="button"
                            onClick={() => setMcqAnswers((prev) => ({ ...prev, [q.id]: letter }))}
                            className={`p-3 rounded-lg text-left text-xs border transition-all flex items-center gap-2.5 ${
                              isSelected
                                ? "bg-indigo-600/30 border-indigo-500 text-white shadow-md shadow-indigo-600/10"
                                : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
                            }`}
                          >
                            <span className="w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center font-bold text-[10px] text-indigo-400 flex-shrink-0">
                              {letter}
                            </span>
                            <span className="leading-snug">{opt}</span>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <textarea
                      placeholder="Write your explanation here..."
                      value={shortAnswer}
                      onChange={(e) => setShortAnswer(e.target.value)}
                      rows={3}
                      className="w-full p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  )}
                </div>
              ))}

              <div className="pt-4 border-t border-slate-800 flex justify-end">
                <button
                  type="button"
                  onClick={handleSubmitQuiz}
                  disabled={isSubmittingQuiz}
                  className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-emerald-600/30 disabled:opacity-50"
                >
                  {isSubmittingQuiz ? (
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <Award className="w-3.5 h-3.5" />
                  )}
                  <span>{isSubmittingQuiz ? "Grading Quiz..." : "Submit for Evaluation"}</span>
                </button>
              </div>
            </div>
          ) : (
            /* Step 5: Evaluation & Adaptive Feedback */
            <div className="space-y-6">
              {evalResult && (
                <>
                  <div
                    className={`p-6 rounded-2xl border text-center ${
                      evalResult.passed
                        ? "bg-emerald-950/20 border-emerald-500/30"
                        : "bg-rose-950/20 border-rose-500/30"
                    }`}
                  >
                    <div className="w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center font-mono font-extrabold text-lg">
                      {evalResult.passed ? (
                        <CheckCircle2 className="w-10 h-10 text-emerald-400" />
                      ) : (
                        <AlertTriangle className="w-10 h-10 text-amber-400" />
                      )}
                    </div>
                    <h3 className="text-xl font-extrabold text-white">
                      Score: {evalResult.score_percentage}%
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">
                      {evalResult.passed
                        ? "Great job! Topic mastery updated in your persistent learner profile."
                        : "Score below 70% threshold. Adaptive replanning has been triggered."}
                    </p>
                  </div>

                  {/* Remedial Lesson Alert if < 70% */}
                  {!evalResult.passed && (
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="text-xs font-bold text-amber-300 uppercase">
                          Adaptive Remedial Lesson Generated
                        </h4>
                        <p className="text-xs text-slate-300 mt-1 leading-relaxed">
                          A targeted revision lesson has been inserted immediately into your active roadmap sprint,
                          and your roadmap version has been incremented.
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="pt-4 flex justify-end">
                    <button
                      type="button"
                      onClick={onClose}
                      className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs"
                    >
                      Done & Return to Roadmap
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
