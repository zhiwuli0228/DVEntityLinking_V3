// doccano-inspired inline mention highlighting: the query is rendered as rich
// text with each mention span colored by its link status. Clicking a span
// selects that mention and drives the rest of the workbench. This is the
// biggest visual departure from the old "mention cards only" UI.

import type { UIMention } from "../lib/adapter";
import type { Status } from "../api/client";

const SPAN_STYLES: Record<Status, string> = {
  linked: "bg-emerald-500/25 text-emerald-100 border-emerald-400/50",
  partial: "bg-amber-500/25 text-amber-100 border-amber-400/50",
  ambiguous: "bg-amber-500/25 text-amber-100 border-amber-400/50",
  no_match: "bg-rose-500/20 text-rose-100 border-rose-400/40 line-through decoration-rose-400/60",
  not_required: "bg-slate-500/20 text-slate-200 border-slate-400/30",
  dependency_failed: "bg-rose-500/20 text-rose-100 border-rose-400/40",
  invalid_input: "bg-rose-500/20 text-rose-100 border-rose-400/40",
};

interface Segment {
  text: string;
  mention?: UIMention;
}

function buildSegments(query: string, mentions: UIMention[]): Segment[] {
  if (!query) return [];
  // Sort by start, then longest first; drop None-span mentions (cannot inline).
  const inline = mentions
    .filter((m) => m.span && m.span[0] >= 0 && m.span[1] <= query.length && m.span[0] < m.span[1])
    .sort((a, b) => a.span![0] - b.span![0] || (b.span![1] - b.span![0]) - (a.span![1] - a.span![0]));

  const segments: Segment[] = [];
  let cursor = 0;
  const occupied = new Set<number>();
  for (const m of inline) {
    const [s, e] = m.span!;
    if ([...Array(e - s).keys()].map((k) => k + s).some((p) => occupied.has(p))) continue;
    if (s > cursor) segments.push({ text: query.slice(cursor, s) });
    segments.push({ text: query.slice(s, e), mention: m });
    for (let p = s; p < e; p++) occupied.add(p);
    cursor = e;
  }
  if (cursor < query.length) segments.push({ text: query.slice(cursor) });
  return segments;
}

export function QueryText({
  query,
  mentions,
  activeMentionIndex,
  onSelect,
}: {
  query: string;
  mentions: UIMention[];
  activeMentionIndex: number | null;
  onSelect: (index: number) => void;
}) {
  if (!query.trim()) return null;
  const segments = buildSegments(query, mentions);
  return (
    <div className="rounded-lg border border-shell-border bg-shell-panelSoft px-3 py-2.5">
      <div className="text-[10px] font-bold uppercase tracking-wider text-accent-teal mb-1">Query · inline mentions</div>
      <p className="text-sm leading-7 text-shell-ink break-words">
        {segments.map((seg, i) =>
          seg.mention ? (
            <button
              key={i}
              type="button"
              onClick={() => onSelect(seg.mention!.index)}
              className={`mx-0.5 px-1 rounded border text-[13px] font-medium ${SPAN_STYLES[seg.mention.status]} ${
                activeMentionIndex === seg.mention.index ? "ring-2 ring-accent-teal/70" : ""
              }`}
              title={`${seg.mention.status}${seg.mention.predicted_type ? " · " + seg.mention.predicted_type : ""}`}
            >
              {seg.text}
            </button>
          ) : (
            <span key={i}>{seg.text}</span>
          )
        )}
      </p>
    </div>
  );
}
