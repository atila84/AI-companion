import { useEffect, useState } from "react";
import { fetchModelCatalog } from "../api/chatClient";
import type { ModelCatalogEntry } from "../types/chat";

interface ModelPickerProps {
  value: string | undefined;
  onChange: (modelId: string | undefined) => void;
}

/** Lets the user pick which model replies, or leave it to backend routing/default. */
export function ModelPicker({ value, onChange }: ModelPickerProps): React.JSX.Element {
  const [models, setModels] = useState<ModelCatalogEntry[]>([]);

  useEffect(() => {
    fetchModelCatalog()
      .then(setModels)
      .catch(() => setModels([]));
  }, []);

  if (models.length === 0) {
    return <></>;
  }

  return (
    <select
      className="model-picker"
      value={value ?? ""}
      onChange={(e) => onChange(e.target.value || undefined)}
    >
      <option value="">Default</option>
      {models.map((model) => (
        <option key={model.id} value={model.id}>
          {model.display_name} ({model.cost_tier}
          {model.uncensored ? ", uncensored" : ""})
        </option>
      ))}
    </select>
  );
}
