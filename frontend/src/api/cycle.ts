import { request, LLM_TIMEOUT_MS } from "./http";
import type { CycleStateResponse } from "./types";

export async function startCycle(
  lessonId: string,
  idempotencyKey?: string
): Promise<CycleStateResponse> {
  return request<CycleStateResponse>("POST", "/cycle/start", {
    body: {
      lesson_id: lessonId,
      idempotency_key: idempotencyKey,
    },
  });
}

export async function getCycleState(cycleId: string): Promise<CycleStateResponse> {
  return request<CycleStateResponse>("GET", `/cycle/${cycleId}`);
}

export async function submitCycleStep(
  cycleId: string,
  stepName: string,
  inputData: unknown
): Promise<CycleStateResponse> {
  return request<CycleStateResponse>("POST", `/cycle/${cycleId}/step`, {
    body: {
      step_name: stepName,
      input_data: inputData,
    },
    timeoutMs: LLM_TIMEOUT_MS,
  });
}
