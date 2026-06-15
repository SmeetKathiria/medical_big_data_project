import { disclaimer } from "./db.js";

export type RagChunk = {
  doc_id: string;
  source_type: string;
  title: string;
  url: string;
  version?: string;
  metadata?: Record<string, unknown>;
  text_chunk: string;
};

export type LlmAnswer = {
  answer: string;
  provider: "openai" | "template";
  model?: string;
  error?: string;
};

export type RerankResult = {
  chunk_id: string;
  relevance_score: number;
  reason: string;
};

export type RerankResponse = {
  provider: "openai";
  model: string;
  results: RerankResult[];
  error?: string;
};

function openAiConfigured() {
  const provider = (process.env.LLM_PROVIDER ?? "").toLowerCase();
  return Boolean(process.env.OPENAI_API_KEY) && !["template", "stub", "none", "off"].includes(provider);
}

function openAiRerankConfigured() {
  const provider = (process.env.RERANK_PROVIDER ?? process.env.LLM_PROVIDER ?? "").toLowerCase();
  return Boolean(process.env.OPENAI_API_KEY) && !["template", "stub", "none", "off"].includes(provider);
}

function chunkContext(chunks: RagChunk[]) {
  return chunks.map((chunk, index) => [
    `[${index + 1}] ${chunk.title}`,
    `source_type: ${chunk.source_type}`,
    `doc_id: ${chunk.doc_id}`,
    `version: ${chunk.version ?? "-"}`,
    `metadata: ${JSON.stringify(chunk.metadata ?? {})}`,
    `url: ${chunk.url}`,
    `excerpt: ${String(chunk.text_chunk ?? "").slice(0, 1600)}`,
  ].join("\n")).join("\n\n");
}

function outputText(payload: any) {
  if (typeof payload.output_text === "string") return payload.output_text;
  const parts = payload.output?.flatMap((item: any) => item.content ?? []) ?? [];
  return parts.map((part: any) => part.text ?? "").filter(Boolean).join("\n").trim();
}

function parseJsonObject(text: string) {
  const trimmed = text.trim();
  try {
    return JSON.parse(trimmed);
  } catch {
    const start = trimmed.indexOf("{");
    const end = trimmed.lastIndexOf("}");
    if (start >= 0 && end > start) return JSON.parse(trimmed.slice(start, end + 1));
    throw new Error("OpenAI response did not contain JSON.");
  }
}

function answerInstructions() {
  return [
    "You are MedIntel, a healthcare source analyst.",
    "Answer only from the source context supplied by the application.",
    "Do not provide diagnosis, treatment instructions, or patient-specific medical advice.",
    "If the context is insufficient, say what is missing instead of guessing.",
    "Cite sources inline using bracket numbers like [1] that correspond to the supplied context.",
    "Do not repeat the standard disclaimer; it is displayed separately in the UI.",
  ].join("\n");
}

function answerInput(question: string, chunks: RagChunk[]) {
  return [
    `Question: ${question}`,
    "",
    "Source context:",
    chunkContext(chunks),
    "",
    "Write a concise answer with citation brackets. Add a brief caveat only when needed for uncertainty or missing evidence, not a generic medical disclaimer.",
  ].join("\n");
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs = Number(process.env.LLM_TIMEOUT_MS ?? 15000)) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timeout);
  }
}

export async function rerankWithOpenAi(question: string, chunks: RagChunk[]): Promise<RerankResponse | null> {
  if (!openAiRerankConfigured() || chunks.length < 2) return null;
  const model = process.env.RERANK_MODEL ?? process.env.OPENAI_MODEL ?? "gpt-4.1-mini";
  const candidates = chunks.map((chunk, index) => ({
    index: index + 1,
    chunk_id: (chunk as any).chunk_id,
    source_type: chunk.source_type,
    title: chunk.title,
    doc_id: chunk.doc_id,
    metadata: chunk.metadata ?? {},
    excerpt: String(chunk.text_chunk ?? "").slice(0, 900),
  }));
  const instructions = [
    "You are a healthcare retrieval reranker.",
    "Score each candidate for how directly it answers the question using only the candidate text and metadata.",
    "Prefer exact policy, label, code, entity, and citation matches over broad topical overlap.",
    "Return strict JSON only with key results.",
    "Each result must include chunk_id, relevance_score from 0 to 1, and a short reason.",
  ].join("\n");
  const input = JSON.stringify({ question, candidates }, null, 2);
  try {
    const response = await fetchWithTimeout("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        instructions,
        input,
        temperature: 0,
        max_output_tokens: 1800,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      return { provider: "openai", model, results: [], error: payload.error?.message ?? `OpenAI API error ${response.status}` };
    }
    const parsed = parseJsonObject(outputText(payload));
    const results = Array.isArray(parsed.results) ? parsed.results : [];
    return {
      provider: "openai",
      model,
      results: results
        .map((item: any) => ({
          chunk_id: String(item.chunk_id ?? ""),
          relevance_score: Math.max(0, Math.min(1, Number(item.relevance_score ?? 0))),
          reason: String(item.reason ?? "").slice(0, 240),
        }))
        .filter((item: RerankResult) => item.chunk_id),
    };
  } catch (error) {
    return { provider: "openai", model, results: [], error: error instanceof Error ? error.message : "OpenAI rerank failed." };
  }
}

export async function answerWithOpenAi(question: string, chunks: RagChunk[]): Promise<LlmAnswer | null> {
  if (!openAiConfigured() || !chunks.length) return null;
  const model = process.env.OPENAI_MODEL ?? "gpt-4.1-mini";

  try {
    const response = await fetchWithTimeout("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        instructions: answerInstructions(),
        input: answerInput(question, chunks),
        temperature: 0.2,
        max_output_tokens: 650,
      }),
    });
    const payload = await response.json();
    if (!response.ok) {
      return { answer: "", provider: "openai", model, error: payload.error?.message ?? `OpenAI API error ${response.status}` };
    }
    const answer = outputText(payload);
    return answer ? { answer, provider: "openai", model } : { answer: "", provider: "openai", model, error: "OpenAI response did not include text." };
  } catch (error) {
    return { answer: "", provider: "openai", model, error: error instanceof Error ? error.message : "OpenAI request failed." };
  }
}

export async function streamAnswerWithOpenAi(
  question: string,
  chunks: RagChunk[],
  onDelta: (delta: string) => void,
): Promise<LlmAnswer | null> {
  if (!openAiConfigured() || !chunks.length) return null;
  const model = process.env.OPENAI_MODEL ?? "gpt-4.1-mini";
  let answer = "";

  try {
    const response = await fetchWithTimeout("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        instructions: answerInstructions(),
        input: answerInput(question, chunks),
        temperature: 0.2,
        max_output_tokens: 650,
        stream: true,
      }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      return { answer: "", provider: "openai", model, error: payload.error?.message ?? `OpenAI API error ${response.status}` };
    }
    if (!response.body) return { answer: "", provider: "openai", model, error: "OpenAI stream did not include a response body." };

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const event of events) {
        const dataLines = event.split("\n")
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trim());
        if (!dataLines.length) continue;
        const data = dataLines.join("\n");
        if (data === "[DONE]") continue;
        const payload = JSON.parse(data);
        const delta = payload.delta ?? payload.output_text_delta ?? "";
        if (payload.type === "response.output_text.delta" && delta) {
          answer += delta;
          onDelta(delta);
        }
        if (payload.type === "response.output_text.done" && payload.text && !answer) {
          answer = payload.text;
          onDelta(payload.text);
        }
        if (payload.type === "error") {
          return { answer, provider: "openai", model, error: payload.error?.message ?? "OpenAI stream failed." };
        }
      }
    }

    return answer ? { answer, provider: "openai", model } : { answer: "", provider: "openai", model, error: "OpenAI stream did not include text." };
  } catch (error) {
    return { answer, provider: "openai", model, error: error instanceof Error ? error.message : "OpenAI streaming request failed." };
  }
}
