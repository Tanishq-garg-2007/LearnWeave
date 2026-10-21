import { request, LLM_TIMEOUT_MS } from "./http";
import type {
  NormalizedQuiz,
  NormalizedQuestion,
  RawQuizResponse,
  QuizAnswerSubmission,
  QuizSubmitResponse,
} from "./types";

export function normalizeQuiz(raw: RawQuizResponse): NormalizedQuiz {
  const questions: NormalizedQuestion[] = (raw.questions || []).map((q) => {
    const optionKeys = q.options ? Object.keys(q.options).sort() : undefined;
    const options = optionKeys && q.options ? optionKeys.map((key) => q.options![key]) : undefined;

    return {
      id: String(q.question_index),
      question_index: q.question_index,
      question_type: q.question_type,
      prompt: q.question,
      options,
      option_keys: optionKeys,
      rubric_criteria: q.rubric_criteria,
    };
  });

  return {
    quiz_id: raw.assessment_id,
    lesson_id: raw.lesson_id,
    title: raw.title,
    questions,
  };
}

export async function generateQuiz(lessonId: string): Promise<NormalizedQuiz> {
  const raw = await request<RawQuizResponse>("POST", `/lessons/${lessonId}/quiz`, {
    timeoutMs: LLM_TIMEOUT_MS,
  });
  return normalizeQuiz(raw);
}

export async function getQuiz(lessonId: string): Promise<NormalizedQuiz> {
  const raw = await request<RawQuizResponse>("GET", `/lessons/${lessonId}/quiz`);
  return normalizeQuiz(raw);
}

export async function submitQuiz(
  lessonId: string,
  assessmentId: string,
  answers: QuizAnswerSubmission[]
): Promise<QuizSubmitResponse> {
  const res = await request<QuizSubmitResponse>("POST", `/lessons/${lessonId}/quiz/submit`, {
    body: {
      assessment_id: assessmentId,
      answers,
    },
    timeoutMs: LLM_TIMEOUT_MS,
  });
  return {
    ...res,
    score_percentage: Math.round((res.overall_score ?? 0) * 100),
  };
}
