// Collapsible raw JSON for debugging. Off by default so it never dominates the
// workbench; expands to reveal the full API payload for developer poking.

import { Card } from "./ui";

export function DebugPanel({
  data,
  collapsed,
  onToggle,
}: {
  data: unknown;
  collapsed: boolean;
  onToggle: (collapsed: boolean) => void;
}) {
  return (
    <Card pad={false} testId="debug-panel">
      <button
        type="button"
        className="w-full flex items-center justify-between px-3 py-2"
        onClick={() => onToggle(!collapsed)}
      >
        <span className="text-[10px] font-bold uppercase tracking-wider text-accent-teal">调试详情</span>
        <span className="text-[11px] text-shell-muted">{collapsed ? "展开" : "折叠"}</span>
      </button>
      {!collapsed && (
        <pre className="border-t border-shell-border px-3 py-2 text-[11px] text-shell-muted whitespace-pre-wrap break-words max-h-96 overflow-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </Card>
  );
}
