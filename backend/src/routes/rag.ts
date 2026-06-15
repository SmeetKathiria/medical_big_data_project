import { Router } from "express";
import crypto from "node:crypto";
import { createReadStream } from "node:fs";
import { createInterface } from "node:readline";
import { activeRunId, disclaimer, lakePath, query } from "../db.js";
import { answerWithOpenAi, rerankWithOpenAi, streamAnswerWithOpenAi } from "../llm.js";

export const rag = Router();

const STOPWORDS = new Set([
  "about",
  "also",
  "and",
  "any",
  "are",
  "cms",
  "does",
  "evidence",
  "fda",
  "for",
  "from",
  "how",
  "into",
  "label",
  "labels",
  "mention",
  "mentions",
  "pubmed",
  "retrieved",
  "say",
  "says",
  "source",
  "sources",
  "the",
  "their",
  "this",
  "what",
  "when",
  "where",
  "with",
]);

type ScoreBreakdown = {
  matched_terms: string[];
  matched_entities: string[];
  lexical_score: number;
  entity_score: number;
  authority_score: number;
  vector_score?: number;
  rerank_score?: number;
  rerank_reason?: string;
  final_score: number;
};

function scoreBreakdown(queryText: string, chunk: any, vectorScore?: number): ScoreBreakdown {
  const q = queryText.toLowerCase();
  const metadata = chunk.metadata ?? {};
  const identifiers = [
    chunk.doc_id,
    chunk.version,
    metadata.pmid,
    metadata.set_id,
    metadata.article_id,
    metadata.lcd_id,
    metadata.ncd_id,
  ].filter(Boolean).map((value) => String(value).toLowerCase());
  const text = `${chunk.title} ${chunk.text_chunk} ${identifiers.join(" ")}`.toLowerCase();
  const terms = q.split(/\W+/).filter((term) => term.length > 2 && !STOPWORDS.has(term));
  const matchedTerms: string[] = [...new Set(terms.filter((term) => text.includes(term)))];
  const matchedEntities: string[] = [...new Set<string>((chunk.entities ?? [])
    .map((entity: any) => String(entity.normalized_value ?? entity.entity_value ?? "").toLowerCase())
    .filter((value: string) => value && q.includes(value)))];
  const exactIdentifierMatches = identifiers.filter((value) => value && q.includes(value));
  const lexicalScore = matchedTerms.length;
  const entityScore = (matchedEntities.length ? 3 : 0) + (exactIdentifierMatches.length ? 12 : 0);
  const authorityScore = lexicalScore || entityScore ? Number(chunk.source_authority_score ?? 0) : 0;
  const finalScore = lexicalScore + entityScore + authorityScore;
  return {
    matched_terms: matchedTerms,
    matched_entities: [...new Set([...matchedEntities, ...exactIdentifierMatches])],
    lexical_score: lexicalScore,
    entity_score: entityScore,
    authority_score: authorityScore,
    vector_score: vectorScore,
    final_score: finalScore,
  };
}

function withScore(queryText: string, chunk: any, retrievalMode: string, vectorScore?: number) {
  const scoring = scoreBreakdown(queryText, chunk, vectorScore);
  return {
    ...chunk,
    retrieval_mode: retrievalMode,
    score: scoring.final_score,
    scoring,
  };
}

function candidateLimit() {
  return Math.max(5, Math.min(50, Number(process.env.RERANK_CANDIDATE_LIMIT ?? 20)));
}

function finalLimit() {
  return Math.max(1, Math.min(10, Number(process.env.RAG_TOP_K ?? 5)));
}

function asksForExactIdentifier(question: string) {
  return /\b(?:pmid\s*)?\d{5,9}\b/i.test(question) || /\b(?:cpt|hcpcs)\s*[a-z]?\d{4,5}\b/i.test(question);
}

async function rerank(question: string, chunks: any[]) {
  if (chunks.length < 2) return { chunks, metadata: { provider: "none", model: null, applied: false } };
  const rerankResponse = await rerankWithOpenAi(question, chunks);
  if (!rerankResponse?.results.length) {
    return {
      chunks,
      metadata: {
        provider: rerankResponse?.provider ?? "none",
        model: rerankResponse?.model ?? null,
        applied: false,
        error: rerankResponse?.error,
      },
    };
  }
  const scores = new Map(rerankResponse.results.map((item) => [item.chunk_id, item]));
  const reranked = chunks
    .map((chunk) => {
      const result = scores.get(chunk.chunk_id);
      const rerankScore = result?.relevance_score ?? 0;
      return {
        ...chunk,
        retrieval_mode: `${chunk.retrieval_mode}+rerank`,
        score: rerankScore,
        scoring: {
          ...chunk.scoring,
          rerank_score: rerankScore,
          rerank_reason: result?.reason,
          final_score: rerankScore,
        },
      };
    })
    .filter((chunk) => chunk.scoring.rerank_score > 0)
    .sort((a, b) => b.scoring.rerank_score - a.scoring.rerank_score);
  return {
    chunks: reranked.length ? reranked : chunks,
    metadata: {
      provider: rerankResponse.provider,
      model: rerankResponse.model,
      applied: Boolean(reranked.length),
      error: rerankResponse.error,
    },
  };
}

function embedText(text: string, dim = 384) {
  const vector = Array.from({ length: dim }, () => 0);
  for (const token of text.toLowerCase().split(/\s+/).filter(Boolean)) {
    const digest = crypto.createHash("sha256").update(token).digest();
    const idx = digest.readUInt32BE(0) % dim;
    const sign = digest[4] % 2 === 0 ? 1 : -1;
    vector[idx] += sign;
  }
  const norm = Math.sqrt(vector.reduce((sum, value) => sum + value * value, 0)) || 1;
  return vector.map((value) => value / norm);
}

async function qdrantSearch(question: string, sourceFilters: Set<string>) {
  const qdrantUrl = process.env.QDRANT_URL ?? "http://localhost:6333";
  const collection = process.env.QDRANT_COLLECTION ?? "medintel_healthcare_v001";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), Number(process.env.QDRANT_TIMEOUT_MS ?? 1200));
  const must = sourceFilters.size
    ? [{ key: "source_type", match: { any: Array.from(sourceFilters) } }]
    : [];
  try {
    const response = await fetch(`${qdrantUrl}/collections/${collection}/points/search`, {
      method: "POST",
      signal: controller.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vector: embedText(question),
        limit: candidateLimit(),
        with_payload: true,
        filter: must.length ? { must } : undefined,
      }),
    });
    if (!response.ok) return [];
    const data = await response.json() as { result?: Array<{ score: number; payload: any }> };
    return (data.result ?? [])
      .map((point) => withScore(question, point.payload, "qdrant_hybrid", point.score))
      .filter((chunk) => chunk.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, candidateLimit());
  } catch {
    return [];
  } finally {
    clearTimeout(timeout);
  }
}

function contextForResponse(chunk: any) {
  return {
    ...chunk,
    entities: (chunk.entities ?? []).slice(0, 10),
    text_chunk: String(chunk.text_chunk ?? "").slice(0, 1800),
  };
}

function answerFor(question: string, chunks: any[]) {
  const lower = question.toLowerCase();
  if (!chunks.length) return "I could not find enough source context to answer confidently.";
  const sources = Array.from(new Set(chunks.map((chunk) => String(chunk.source_type).toUpperCase()))).join(", ");
  const titles = chunks.slice(0, 3).map((chunk) => chunk.title).filter(Boolean).join("; ");
  if (lower.includes("changed") || lower.includes("2024") || lower.includes("2025")) {
    return "I found CMS context, but not enough related policy versions to make a version-change claim. Use the citations to inspect the current CMS documents, or load the full CMS version history before comparing policy changes.";
  }
  if (lower.includes("72148") || lower.includes("medical necessity")) {
    return `I found CMS documents related to CPT 72148. Treat coverage or medical-necessity requirements as citation-specific and verify the exact language in the linked CMS article before relying on it. Sources: ${titles || sources}.`;
  }
  if (lower.includes("glp") || lower.includes("obesity") || lower.includes("semaglutide")) {
    return `I found ${sources} context related to GLP-1, semaglutide, or obesity. Use the citations to inspect the exact source type and label language before drawing clinical or policy conclusions.`;
  }
  return "The sources provide useful context, but not enough support to make a more specific claim confidently.";
}

async function fallbackSearch(question: string, sourceFilters: Set<string>) {
  const corpusPath = lakePath("retrieval", "corpus", `${activeRunId()}.jsonl`);
  const top: any[] = [];
  const rl = createInterface({ input: createReadStream(corpusPath), crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line.trim()) continue;
    const chunk = JSON.parse(line);
    if (sourceFilters.size && !sourceFilters.has(chunk.source_type)) continue;
    const scored = withScore(question, chunk, "streaming_lexical");
    if (scored.score <= 0) continue;
    top.push(scored);
    top.sort((a, b) => b.score - a.score);
    if (top.length > candidateLimit()) top.pop();
  }
  return top;
}

function mergeCandidates(candidates: any[][]) {
  const byChunkId = new Map<string, any>();
  for (const chunk of candidates.flat()) {
    const existing = byChunkId.get(chunk.chunk_id);
    if (!existing || Number(chunk.score ?? 0) > Number(existing.score ?? 0)) {
      byChunkId.set(chunk.chunk_id, chunk);
      continue;
    }
    const modes = new Set(String(existing.retrieval_mode ?? "").split("+").filter(Boolean));
    for (const mode of String(chunk.retrieval_mode ?? "").split("+").filter(Boolean)) modes.add(mode);
    existing.retrieval_mode = Array.from(modes).join("+");
  }
  return Array.from(byChunkId.values())
    .sort((a, b) => Number(b.score ?? 0) - Number(a.score ?? 0))
    .slice(0, candidateLimit());
}

async function retrieveEvidence(question: string, filters: any = {}) {
  const sourceFilters = new Set<string>(filters.sources ?? []);
  const qdrantChunks = await qdrantSearch(question, sourceFilters);
  const lexicalChunks = qdrantChunks.length >= candidateLimit() && !asksForExactIdentifier(question)
    ? []
    : await fallbackSearch(question, sourceFilters);
  let chunks = mergeCandidates([qdrantChunks, lexicalChunks]);
  let retrievalMode = qdrantChunks.length && lexicalChunks.length ? "qdrant_hybrid+streaming_lexical" : qdrantChunks.length ? "qdrant_hybrid" : "streaming_lexical";
  const reranked = await rerank(question, chunks);
  chunks = reranked.chunks.slice(0, finalLimit()).map((chunk, index) => ({ ...chunk, rank: index + 1 }));
  if (reranked.metadata.applied) retrievalMode = `${retrievalMode}+rerank`;
  const citations = chunks.map((chunk) => ({
    doc_id: chunk.doc_id,
    title: chunk.title,
    url: chunk.url,
    source_type: chunk.source_type,
    version: chunk.version,
  }));
  const retrievedContext = chunks.map(contextForResponse);
  return {
    chunks,
    citations,
    retrievedContext,
    retrieval: {
      mode: retrievalMode,
      scoring_version: reranked.metadata.applied ? "hybrid_v2_rerank" : "hybrid_v2",
      rank_count: chunks.length,
      candidate_count: reranked.metadata.applied ? reranked.chunks.length : chunks.length,
      reranker: reranked.metadata,
      formula: reranked.metadata.applied
        ? "Score uses the reranker relevance estimate; lexical, entity, authority, and vector values are shown as supporting signals."
        : "Score combines matched terms, entity matches, and source authority. Vector score is shown separately when available.",
    },
  };
}

async function persistQuery(question: string, answer: string, citations: any[], retrievedContext: any[], latencyMs: number) {
  await query("INSERT INTO rag_queries (query, answer, citations, retrieved_context, latency_ms) VALUES ($1, $2, $3, $4, $5)", [
    question,
    answer,
    JSON.stringify(citations),
    JSON.stringify(retrievedContext),
    latencyMs,
  ]);
}

function streamEvent(res: any, event: string, data: any) {
  res.write(`event: ${event}\n`);
  res.write(`data: ${JSON.stringify(data)}\n\n`);
}

async function streamText(answer: string, onDelta: (delta: string) => void) {
  const parts = answer.match(/\S+\s*/g) ?? [answer];
  for (const part of parts) {
    onDelta(part);
    await new Promise((resolve) => setTimeout(resolve, 18));
  }
}

rag.post("/query", async (req, res) => {
  const started = Date.now();
  const { question, filters = {} } = req.body ?? {};
  const evidence = await retrieveEvidence(question ?? "", filters);
  const llmAnswer = await answerWithOpenAi(question ?? "", evidence.retrievedContext);
  const answer = llmAnswer?.answer || answerFor(question ?? "", evidence.chunks);
  const response = {
    answer,
    answer_provider: llmAnswer?.answer ? llmAnswer.provider : "template",
    answer_model: llmAnswer?.answer ? llmAnswer.model : undefined,
    answer_warning: llmAnswer?.error,
    citations: evidence.citations,
    retrieved_context: evidence.retrievedContext,
    retrieval: evidence.retrieval,
    disclaimer,
    latency_ms: Date.now() - started,
  };
  await persistQuery(question, answer, evidence.citations, evidence.retrievedContext, response.latency_ms);
  res.json(response);
});

rag.post("/query/stream", async (req, res) => {
  const started = Date.now();
  const { question, filters = {} } = req.body ?? {};
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache, no-transform");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders?.();

  try {
    streamEvent(res, "status", { label: "Retrieving sources" });
    const evidence = await retrieveEvidence(question ?? "", filters);
    streamEvent(res, "status", { label: "Writing the brief" });
    streamEvent(res, "metadata", {
      answer_provider: "stream",
      citations: evidence.citations,
      retrieved_context: evidence.retrievedContext,
      retrieval: evidence.retrieval,
      disclaimer,
    });

    let answer = "";
    const llmAnswer = await streamAnswerWithOpenAi(question ?? "", evidence.retrievedContext, (delta) => {
      answer += delta;
      streamEvent(res, "answer_delta", { delta });
    });

    let provider = "template";
    let model: string | undefined;
    let warning = llmAnswer?.error;
    if (llmAnswer?.answer) {
      answer = llmAnswer.answer;
      provider = llmAnswer.provider;
      model = llmAnswer.model;
    } else {
      answer = answerFor(question ?? "", evidence.chunks);
      await streamText(answer, (delta) => streamEvent(res, "answer_delta", { delta }));
    }

    const latencyMs = Date.now() - started;
    await persistQuery(question, answer, evidence.citations, evidence.retrievedContext, latencyMs);
    streamEvent(res, "done", {
      answer_provider: provider,
      answer_model: model,
      answer_warning: warning,
      latency_ms: latencyMs,
    });
  } catch (error) {
    streamEvent(res, "error", { message: error instanceof Error ? error.message : "The brief could not be generated." });
  } finally {
    res.end();
  }
});

rag.post("/feedback", async (req, res) => {
  await query("UPDATE rag_queries SET feedback = $1 WHERE id = $2", [req.body.feedback, req.body.id]);
  res.json({ ok: true });
});
