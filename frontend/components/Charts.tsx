"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis } from "recharts";

export function SourceChart({ data }: { data: { name: string; value: number }[] }) {
  return (
    <div className="diagnostic-shell">
      <div className="surface-card h-72 p-4">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <div className="eyebrow">Source Distribution</div>
            <div className="mt-1 font-serif text-2xl font-light text-ink">Documents by corpus</div>
          </div>
          <span className="status-pill">LIVE FEED</span>
        </div>
        <ResponsiveContainer width="100%" height="80%">
          <BarChart data={data}>
            <XAxis dataKey="name" stroke="#65616f" tickLine={false} axisLine={false} />
            <YAxis allowDecimals={false} stroke="#65616f" tickLine={false} axisLine={false} />
            <Bar dataKey="value" fill="#19a974" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
