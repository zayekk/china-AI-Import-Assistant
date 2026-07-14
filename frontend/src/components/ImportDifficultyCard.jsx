import React from "react";
import { Ship } from "lucide-react";
import clsx from "clsx";

// Clés alignées sur import_difficulty côté serveur. Structure calquée sur COMPETITION_META
// (CompetitionCard.jsx) / SATURATION_META (SaturationCard.jsx), mais 4 valeurs distinctes.
const DIFFICULTY_META = {
  very_easy: { emoji: "🟢", label: "Très facile", classes: "bg-green-50 text-green-800 border-green-200" },
  easy: { emoji: "🟡", label: "Facile", classes: "bg-yellow-50 text-yellow-800 border-yellow-200" },
  medium: { emoji: "🟠", label: "Moyen", classes: "bg-orange-50 text-orange-800 border-orange-200" },
  hard: { emoji: "🔴", label: "Difficile", classes: "bg-red-50 text-red-800 border-red-200" },
};

/**
 * Difficulté estimée pour importer ce produit (réglementation, formalités, restrictions).
 */
export default function ImportDifficultyCard({ level, explanation }) {
  if (!level) return null;
  const config = DIFFICULTY_META[level] || DIFFICULTY_META.medium;

  return (
    <div className={clsx("rounded-xl border p-4 space-y-1.5", config.classes)}>
      <h3 className="flex items-center gap-2 text-sm font-semibold">
        <Ship size={16} /> Difficulté d'importation
      </h3>
      <p className="text-lg font-bold">
        {config.emoji} {config.label}
      </p>
      {explanation && <p className="text-sm">{explanation}</p>}
    </div>
  );
}
