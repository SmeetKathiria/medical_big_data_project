"use client";

import { useState } from "react";
import { FileDiff } from "lucide-react";
import { api } from "./api";
import { CitationPanel } from "./CitationPanel";

export function PolicyCompare({ initialDiff }: { initialDiff: any }) {
  const [topic, setTopic] = useState("lumbar spine MRI");
  const [diff, setDiff] = useState(initialDiff);
  async function loadDiff() {
    setDiff(await api(`/api/policies/diff?topic=${encodeURIComponent(topic)}`));
  }
  return (
    <div className="grid gap-5 lg:grid-cols-[380px_1fr]">
      <div className="diagnostic-shell">
        <div className="surface-card p-5">
          <label className="eyebrow">Topic or code</label>
          <input value={topic} onChange={(event) => setTopic(event.target.value)} className="input-field mt-3 h-12 w-full" />
          <button onClick={loadDiff} className="btn-primary mt-4">
            <FileDiff size={16} />
            Compare
          </button>
        </div>
      </div>
      <div className="space-y-5">
        <div className="surface-card p-5">
          <h2 className="section-title">Summary</h2>
          <p className="mt-4 text-sm font-light leading-7 text-muted">{diff?.summary}</p>
        </div>
        <CitationPanel citations={diff?.diff_json?.citations ?? []} />
      </div>
    </div>
  );
}
