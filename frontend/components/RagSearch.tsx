"use client";

import { useEffect, useState } from "react";
import { Search, X } from "lucide-react";
import { API_URL } from "./api";
import { CitationPanel } from "./CitationPanel";
import { RetrievalScoringPanel } from "./RetrievalScoringPanel";

const searchStateKey = "medintel:intel-lens:last-search";

function mergeResult(current: any, next: any) {
  return { ...(current ?? {}), ...next };
}

function briefBadge(result: any, loading: boolean) {
  if (!result) return "";
  if (loading) return "Evidence review";
  if (result.answer) return "Citation-backed";
  return "";
}

const sourceLabels: Record<string, string> = {
  cms: "CMS",
  fda: "FDA",
  pubmed: "PubMed",
};

const exampleQuestions = [
  {
    label: "CMS coverage policy",
    question: "Which CMS articles discuss CPT 72148 and lumbar MRI coverage?",
    sources: ["cms"],
  },
  {
    label: "FDA label review",
    question: "What do FDA labels say about semaglutide indications, obesity use, and major warnings?",
    sources: ["fda"],
  },
  {
    label: "PubMed study findings",
    question: "What did PubMed PMID 937819 find about emphysema-like lung changes in blotchy mice?",
    sources: ["pubmed"],
  },
  {
    label: "Label and literature alignment",
    question: "Compare FDA label language about semaglutide with PubMed obesity evidence in this corpus.",
    sources: ["fda", "pubmed"],
  },
];

type LensState = {
  question: string;
  sources: string[];
  result: any;
  loading: boolean;
  loadingStage: string;
  briefComplete: boolean;
};

const initialLensState: LensState = {
  question: "",
  sources: ["cms"],
  result: null,
  loading: false,
  loadingStage: "",
  briefComplete: false,
};

let lensState: LensState = { ...initialLensState };
let activeRequestId = 0;
let activeAbortController: AbortController | null = null;
const lensSubscribers = new Set<(state: LensState) => void>();

function persistLensState(state: LensState) {
  if (typeof window === "undefined") return;
  if (!state.question && !state.result) {
    window.sessionStorage.removeItem(searchStateKey);
    return;
  }
  window.sessionStorage.setItem(searchStateKey, JSON.stringify({
    question: state.question,
    sources: state.sources,
    result: state.result,
    loading: state.loading,
    loadingStage: state.loadingStage,
    briefComplete: state.briefComplete,
  }));
}

function publishLensState(next: LensState) {
  lensState = next;
  persistLensState(next);
  lensSubscribers.forEach((subscriber) => subscriber(lensState));
}

function updateLensState(updater: (current: LensState) => LensState) {
  publishLensState(updater(lensState));
}

function hydrateLensState() {
  if (typeof window === "undefined") return lensState;
  const saved = window.sessionStorage.getItem(searchStateKey);
  if (!saved) return lensState;
  try {
    const parsed = JSON.parse(saved);
    if (parsed.result?.answer && !String(parsed.question ?? "").trim()) {
      window.sessionStorage.removeItem(searchStateKey);
      return lensState;
    }
    lensState = {
      question: typeof parsed.question === "string" ? parsed.question : "",
      sources: Array.isArray(parsed.sources) && parsed.sources.length ? parsed.sources : ["cms"],
      result: parsed.result ?? null,
      loading: activeAbortController ? Boolean(parsed.loading) : false,
      loadingStage: activeAbortController ? String(parsed.loadingStage ?? "") : "",
      briefComplete: Boolean(parsed.briefComplete || parsed.result?.answer),
    };
  } catch {
    window.sessionStorage.removeItem(searchStateKey);
  }
  return lensState;
}

function subscribeLensState(subscriber: (state: LensState) => void) {
  lensSubscribers.add(subscriber);
  subscriber(lensState);
  return () => {
    lensSubscribers.delete(subscriber);
  };
}

function isCurrentRequest(requestId: number) {
  return activeRequestId === requestId;
}

function handleStreamEvent(event: string, payload: any, requestId: number) {
  if (!isCurrentRequest(requestId)) return;
  if (event === "status") {
    updateLensState((current) => ({ ...current, loadingStage: payload.label ?? "Working" }));
    return;
  }
  if (event === "metadata") {
    updateLensState((current) => ({ ...current, result: mergeResult(current.result, payload) }));
    return;
  }
  if (event === "answer_delta") {
    updateLensState((current) => ({
      ...current,
      result: { ...(current.result ?? {}), answer: `${current.result?.answer ?? ""}${payload.delta ?? ""}` },
    }));
    return;
  }
  if (event === "done") {
    updateLensState((current) => ({
      ...current,
      result: mergeResult(current.result, payload),
      briefComplete: true,
      loadingStage: "",
    }));
    return;
  }
  if (event === "error") {
    updateLensState((current) => ({
      ...current,
      result: mergeResult(current.result, { answer_warning: payload.message ?? "The brief could not be generated." }),
      briefComplete: true,
      loadingStage: "",
    }));
  }
}

async function readStream(response: Response, requestId: number) {
  if (!response.body) throw new Error("Streaming response did not include a body.");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    if (!isCurrentRequest(requestId)) {
      await reader.cancel().catch(() => undefined);
      return;
    }
    const { value, done } = await reader.read();
    if (!isCurrentRequest(requestId)) {
      await reader.cancel().catch(() => undefined);
      return;
    }
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";
    for (const rawEvent of events) {
      const lines = rawEvent.split("\n");
      const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim() ?? "message";
      const data = lines.filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
      if (!data) continue;
      handleStreamEvent(event, JSON.parse(data), requestId);
    }
  }
}

function clearLensSearch() {
  activeRequestId += 1;
  activeAbortController?.abort();
  activeAbortController = null;
  publishLensState({ ...initialLensState });
}

async function startLensSearch(question: string, sources: string[]) {
  if (!question.trim()) return;
  activeAbortController?.abort();
  const requestId = activeRequestId + 1;
  activeRequestId = requestId;
  const abortController = new AbortController();
  activeAbortController = abortController;
  publishLensState({
    question,
    sources,
    loading: true,
    briefComplete: false,
    loadingStage: "Retrieving evidence",
    result: {
      answer: "",
      answer_provider: "active",
      citations: [],
      retrieved_context: [],
      retrieval: null,
      disclaimer: "For healthcare research and evidence review only. Not medical advice, diagnosis, treatment guidance, or a substitute for clinician judgment.",
    },
  });
  try {
    const response = await fetch(`${API_URL}/api/rag/query/stream`, {
      method: "POST",
      cache: "no-store",
      signal: abortController.signal,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, filters: { sources } }),
    });
    if (!isCurrentRequest(requestId)) return;
    if (!response.ok) throw new Error(`API error ${response.status}`);
    await readStream(response, requestId);
  } catch (error) {
    if (!isCurrentRequest(requestId) || abortController.signal.aborted) return;
    updateLensState((current) => ({
      ...current,
      result: mergeResult(current.result, {
        answer_warning: error instanceof Error ? error.message : "The review could not be completed.",
      }),
      briefComplete: true,
    }));
  } finally {
    if (isCurrentRequest(requestId)) {
      activeAbortController = null;
      updateLensState((current) => ({ ...current, loading: false, loadingStage: "" }));
    }
  }
}

export function RagSearch() {
  const [state, setState] = useState< LensState >(lensState);
  const { question, sources, result, loading, loadingStage, briefComplete } = state;

  useEffect(() => {
    setState(hydrateLensState());
    return subscribeLensState(setState);
  }, []);

  function toggle(source: string) {
    updateLensState((current) => ({
      ...current,
      sources: current.sources.includes(source) ? current.sources.filter((item) => item !== source) : [...current.sources, source],
    }));
  }

  function useExample(example: { question: string; sources: string[] }) {
    updateLensState((current) => ({ ...current, question: example.question, sources: example.sources }));
  }

  function clearSearch() {
    clearLensSearch();
  }

  async function submit() {
    await startLensSearch(question, sources);
  }

  return (
    <div className="min-w-0 space-y-5">
      <div className="grid min-w-0 items-stretch gap-5 lg:grid-cols-[minmax(320px,440px)_minmax(0,1fr)]">
        <div className="diagnostic-shell min-w-0 self-stretch">
          <div className="surface-card flex h-full flex-col p-5">
            <div>
              <label className="eyebrow">Clinical Review Question</label>
              <textarea value={question} onChange={(event) => updateLensState((current) => ({ ...current, question: event.target.value }))} placeholder="Ask about coverage policy, label language, safety signals, or published evidence." className="input-field mt-3 min-h-36 w-full py-4" />
              <div className="mt-4 rounded-[24px] border border-line/70 bg-white/45 p-4">
                <div className="eyebrow">Common review paths</div>
                <div className="mt-2 grid gap-2">
                  {exampleQuestions.map((example) => (
                    <button key={example.label} type="button" onClick={() => useExample(example)} className="rounded-full border border-line/70 bg-white/70 px-4 py-2.5 text-left text-sm font-medium leading-5 text-ink transition hover:border-green/50 hover:bg-mint">
                      {example.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="mt-4 shrink-0 border-t border-line/70 pt-4">
              <div className="flex flex-wrap gap-2">
                {["cms", "fda", "pubmed"].map((source) => (
                  <button key={source} onClick={() => toggle(source)} className={`btn-toggle ${sources.includes(source) ? "border-green bg-green text-panel shadow-[0_18px_32px_-24px_rgba(28,50,45,0.9)]" : "border-line/70 bg-white/60 text-muted hover:border-green/50 hover:text-green"}`}>
                    {sourceLabels[source] ?? source}
                  </button>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button onClick={submit} disabled={loading || !question.trim()} className="btn-primary">
                  {loading ? <span className="search-spinner" aria-hidden="true" /> : <Search size={16} />}
                  {loading ? loadingStage || "Reviewing" : "Review"}
                </button>
                {(question || result) && (
                  <button type="button" onClick={clearSearch} className="btn-secondary">
                    <X size={16} />
                    Clear
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="min-w-0 self-stretch lg:sticky lg:top-24">
          <div className={`brief-card flex max-h-[560px] flex-col p-6 sm:p-7 lg:h-full lg:max-h-none ${loading ? "brief-is-loading" : ""}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-serif text-[30px] font-normal leading-tight text-ink sm:text-[38px]">Intel Brief</h2>
            {briefBadge(result, loading) && <span className="status-pill">{briefBadge(result, loading)}</span>}
            </div>
            {loading && !result?.answer && (
              <div className="brief-activity mt-4">
                <div className="flex items-center justify-between gap-3">
                  <span>{loadingStage || "Reviewing sources"}</span>
                  <span className="brief-dots"><i /><i /><i /></span>
                </div>
                <div className="mt-4 space-y-2">
                  <span className="activity-bar w-[92%]" />
                  <span className="activity-bar w-[76%]" />
                  <span className="activity-bar w-[84%]" />
                </div>
              </div>
            )}
            <div className="mt-5 min-h-0 flex-1 overflow-y-auto pr-2">
              <p className="whitespace-pre-line text-[16px] font-light leading-8 text-ink/86">
                {result?.answer ? <>{result.answer}<span className={loading ? "stream-caret" : "hidden"} /></> : !loading ? "Choose a review path or ask a clinical evidence question to generate an Intel Brief." : ""}
              </p>
            </div>
            {result?.answer_warning && <p className="mt-4 rounded-2xl border border-amber/40 bg-amber/15 p-3 text-sm text-ink">{result.answer_warning}</p>}
            {result?.disclaimer && <p className="mt-5 border-t border-line/80 pt-4 text-sm font-light leading-6 text-muted">{result.disclaimer}</p>}
          </div>
        </div>
      </div>

      {result && briefComplete && (
        <div className="intel-followup-reveal min-w-0">
          <CitationPanel citations={result?.citations ?? []} />
        </div>
      )}

      <div className="min-w-0">
        {!result && <RetrievalScoringPanel retrieval={undefined} chunks={[]} />}
        {result && !briefComplete && (
          <section className="intel-followup-wait surface-card p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <div className="eyebrow">Signal Trace</div>
                <p className="mt-2 text-sm text-muted">Citation candidates, matched terms, and ranking rationale will appear once the brief is complete.</p>
              </div>
              <span className="brief-dots"><i /><i /><i /></span>
            </div>
          </section>
        )}
        {result && briefComplete && (
          <div className="intel-followup-reveal">
            <RetrievalScoringPanel retrieval={result?.retrieval} chunks={result?.retrieved_context ?? []} />
          </div>
        )}
      </div>
    </div>
  );
}
