import React from "react";
import { Swords } from "lucide-react";
import clsx from "clsx";

// Clés STRICTEMENT alignées sur _normalize_competition_level() côté serveur
// (ai_engine/services/product_analysis_service.py). Réutilisé aussi par MarketPositionCard.
export const COMPETITION_META = {
  low: { emoji: "🟢", label: "Faible", classes: "bg-green-50 text-green-800 border-green-200" },
  medium: { emoji: "🟡", label: "Moyenne", classes: "bg-yellow-50 text-yellow-800 border-yellow-200" },
  high: { emoji: "🟠", label: "Forte", classes: "bg-orange-50 text-orange-800 border-orange-200" },
  very_high: { emoji: "🔴", label: "Très forte", classes: "bg-red-50 text-red-800 border-red-200" },
};

export default function CompetitionCard({ level, explanation }) {
  const config = COMPETITION_META[level] || COMPETITION_META.medium;

  return (
    <div className={clsx("rounded-xl border p-4 space-y-1.5", config.classes)}>
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <Swords size={16} /> Indice de concurrence
      </h3>
      <p className="text-lg font-bold">
        {config.emoji} {config.label}
      </p>
      {explanation && <p className="text-sm">{explanation}</p>}
    </div>
  );
}
