import React from "react";
import { BarChart3 } from "lucide-react";
import clsx from "clsx";

// Clés alignées sur saturation_level côté serveur (contrat IA). Structure calquée sur
// COMPETITION_META (CompetitionCard.jsx), mais 4 valeurs distinctes du niveau de concurrence.
const SATURATION_META = {
  low: { emoji: "🟢", label: "Peu vendu", classes: "bg-green-50 text-green-800 border-green-200" },
  competitive: { emoji: "🟡", label: "Concurrentiel", classes: "bg-yellow-50 text-yellow-800 border-yellow-200" },
  saturated: { emoji: "🟠", label: "Saturé", classes: "bg-orange-50 text-orange-800 border-orange-200" },
  extremely_saturated: {
    emoji: "🔴",
    label: "Extrêmement saturé",
    classes: "bg-red-50 text-red-800 border-red-200",
  },
};

/**
 * Niveau de saturation du marché pour ce produit, estimé par l'IA.
 */
export default function SaturationCard({ level, explanation }) {
  if (!level) return null;
  const config = SATURATION_META[level] || SATURATION_META.competitive;

  return (
    <div className={clsx("rounded-xl border p-4 space-y-1.5", config.classes)}>
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <BarChart3 size={16} /> Niveau de saturation
      </h3>
      <p className="text-lg font-bold">
        {config.emoji} {config.label}
      </p>
      {explanation && <p className="text-sm">{explanation}</p>}
    </div>
  );
}
