import type { CatalogEntry } from "../types/chat";

interface CatalogPickerProps {
  /** Short label shown beside the select, e.g. "Chat". */
  label: string;
  /** Entries to offer. Empty renders a disabled select showing `emptyHint`. */
  entries: CatalogEntry[];
  value: string | undefined;
  onChange: (id: string | undefined) => void;
  /** Explains why nothing is selectable when `entries` is empty. */
  emptyHint?: string;
}

function optionLabel(entry: CatalogEntry): string {
  return `${entry.display_name} (${entry.cost_tier}${entry.uncensored ? ", uncensored" : ""})`;
}

/**
 * One labeled dropdown over a backend catalog (text, image, or video).
 *
 * Presentational only — the parent owns fetching and selection state, so a
 * single implementation serves all three modalities. Selecting the blank
 * "Default" option clears the choice (`undefined`), letting the backend apply
 * its own routing/default rather than pinning a model client-side.
 */
export function CatalogPicker({
  label,
  entries,
  value,
  onChange,
  emptyHint,
}: CatalogPickerProps): React.JSX.Element {
  const isEmpty = entries.length === 0;

  return (
    <label className="catalog-picker">
      <span className="catalog-picker-label">{label}</span>
      <select
        value={value ?? ""}
        disabled={isEmpty}
        onChange={(e) => onChange(e.target.value || undefined)}
      >
        {isEmpty ? (
          <option value="">{emptyHint ?? "none available"}</option>
        ) : (
          <>
            <option value="">Default</option>
            {entries.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {optionLabel(entry)}
              </option>
            ))}
          </>
        )}
      </select>
    </label>
  );
}
