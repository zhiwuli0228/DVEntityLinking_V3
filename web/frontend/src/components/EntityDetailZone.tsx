// Detail zone (right column, top): selected entity detail (safe projection)
// plus Top-K similar entities. V3 storage_lookup is surfaced when present.

import type { RetrievalResult, SafeEntity } from "../api/client";
import { Card, SectionTitle, Metric, EmptyHint, Badge } from "./ui";

export function EntityDetailZone({
  entity,
  retrieval,
  loadingEntity,
}: {
  entity: SafeEntity | null;
  retrieval: RetrievalResult | null;
  loadingEntity: boolean;
}) {
  return (
    <Card testId="entity-detail-zone">
      <SectionTitle kicker="Entity detail zone" title="实体详情" />
      {!entity && (
        <EmptyHint>{loadingEntity ? "Loading…" : "No linked entity."}</EmptyHint>
      )}
      {entity && (
        <div className="flex flex-col gap-2">
          <dl className="grid grid-cols-2 gap-2">
            <Metric label="entity_id" value={entity.entity_id} />
            <Metric label="entity_type" value={entity.entity_type} />
            <Metric label="canonical_name" value={entity.canonical_name} />
            <Metric label="aliases" value={entity.aliases.join(", ") || "-"} />
          </dl>
          {entity.description && (
            <p className="text-xs text-shell-muted break-words">{entity.description}</p>
          )}
          <div>
            <div className="text-[10px] font-bold uppercase tracking-wider text-shell-muted mb-1">safe attributes</div>
            {entity.attributes_safe && entity.attributes_safe.length > 0 ? (
              <ul className="flex flex-col gap-1">
                {entity.attributes_safe.map((a) => (
                  <li key={a.key} className="rounded-md border border-shell-border bg-shell-panelSoft px-2 py-1 text-xs">
                    <span className="font-semibold text-shell-ink">{a.key}</span>:{" "}
                    <span className="text-shell-ink break-words">{String(a.value)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <EmptyHint>No safe attributes.</EmptyHint>
            )}
            {typeof entity.omitted_attribute_count === "number" && (
              <div className="text-[10px] text-shell-muted mt-1">omitted_attribute_count: {entity.omitted_attribute_count}</div>
            )}
          </div>
          {retrieval && retrieval.items.length > 0 && (
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider text-shell-muted mb-1">similar entities</div>
              <ul className="flex flex-col gap-1">
                {retrieval.items.map((it) => (
                  <li key={it.entity_id} className="rounded-md border border-shell-border bg-shell-panelSoft px-2 py-1 text-xs">
                    <span className="font-semibold text-shell-ink">{it.entity_id}</span>{" "}
                    <span className="text-shell-ink">{it.canonical_name}</span>
                    <div className="text-[10px] text-shell-muted break-words">{it.entity_type} · {it.similarity_reason}</div>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex flex-wrap gap-1 pt-1">
            <Badge tone="slate">{entity.data_layer}</Badge>
            <Badge tone="slate">{entity.source}</Badge>
          </div>
        </div>
      )}
    </Card>
  );
}
