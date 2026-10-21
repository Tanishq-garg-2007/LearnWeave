import { rawRequest, request, LLM_TIMEOUT_MS } from "./http";

export async function speak(text: string, voice = "af_heart"): Promise<Blob> {
  const res = await rawRequest("POST", "/voice/speak", {
    body: { text: text.slice(0, 5000), voice },
    timeoutMs: LLM_TIMEOUT_MS,
  });
  const engine = res.headers.get("X-Audio-Engine") || "kokoro-82m";
  const blob = await res.blob();
  (blob as any).engine = engine;
  return blob;
}

export async function listen(audioBlob: Blob): Promise<{ transcription: string }> {
  const type = audioBlob.type || "audio/webm";
  const ext = type.includes("mp4")
    ? "mp4"
    : type.includes("ogg")
    ? "ogg"
    : type.includes("wav")
    ? "wav"
    : "webm";

  const formData = new FormData();
  formData.append("file", audioBlob, `audio.${ext}`);

  const res = await request<{ text: string }>("POST", "/voice/listen", {
    body: formData,
    timeoutMs: LLM_TIMEOUT_MS,
  });
  return { transcription: res.text ?? "" };
}
