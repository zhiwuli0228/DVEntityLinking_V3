// Catalog filter zone (left column, below query): type-count chips and the
// entity list. Selecting an entity drives the detail zone through shared state.

import type { EntitiesResponse, SafeEntity } from "../api/client";
import { Card, SectionTitle, EmptyHint } from "./ui";

export function CatalogFilterZone({
  catalog,
  activeTypeFilter,
  onSelectType,
  onSelectEntity,
  activeEntityId,
}: {
  catalog: EntitiesResponse | null;
  activeTypeFilter: string;
  onSelectType: (t: string) => void;
  onSelectEntity: (id: string) => void;
  activeEntityId: string | null;
}) {
  const typeCounts = catalog?.type_counts ?? {};
  const items: SafeEntity[] = catalog?.items ?? [];
  return (
    <Card testId="catalog-filter-zone">
      <SectionTitle kicker="Catalog filter zone" title="样例实体目录" />
      <div className="flex flex-wrap gap-1 mb-2">
        <button
          type="button"
          onClick={() => onSelectType("")}
          className={`rounded-full px-2 py-0.5 text-[11px] border ${
            activeTypeFilter === ""
              ? "border-accent-teal/70 bg-accent-teal/10 text-accent-teal"
              : "border-shell-border bg-shell-panelSoft text-shell-muted"
          }`}
        >
          all
        </button>
        {Object.entries(typeCounts).map(([t, n]) => (
          <button
            key={t}
            type="button"
            onClick={() => onSelectType(t)}
            className={`rounded-full px-2 py-0.5 text-[11px] border ${
              activeTypeFilter === t
                ? "border-accent-teal/70 bg-accent-teal/10 text-accent-teal"
                : "border-shell-border bg-shell-panelSoft text-shell-muted"
            }`}
          >
            {t} · {n}
          </button>
        ))}
      </div>
      <div className="max-h-72 overflow-y-auto pr-1">
        {items.length === 0 ? (
          <EmptyHint>No entities.</EmptyHint>
        ) : (
          <ul className="flex flex-col gap-1">
            {items.map((it) => (
              <li key={it.entity_id}>
                <button
                  type="button"
                  onClick={() => onSelectEntity(it.entity_id)}
                  className={`w-full text-left rounded-md border px-2 py-1.5 ${
                    activeEntityId === it.entity_id
                      ? "border-accent-teal/70 bg-accent-teal/10"
                      : "border-shell-border bg-shell-panelSoft hover:border-shell-borderStrong"
                  }`}
                >
                  <div className="text-xs font-semibold text-shell-ink break-words">{it.entity_id}</div>
                  <div className="text-[11px] text-shell-ink break-words">{it.canonical_name}</div>
                  <div className="text-[10px] text-shell-muted">{it.entity_type}</div>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  );
}
