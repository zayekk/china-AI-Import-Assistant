import React from "react";
import { LineChart } from "lucide-react";
import { COMPETITION_META } from "./CompetitionCard";

const POSITIONING_LABELS = {
  premium: "Produit premium",
  mid_range: "Milieu de gamme",
  entry_level: "Entrée de gamme",
  saturated: "Marché saturé",
  unknown: "Indéterminé",
};

/**
 * "Comparaison avec le marché" : concurrence (réutilise competition_level, pas un second champ
 * dupliqué), prix moyen constaté et positionnement (premium / milieu de gamme / entrée de
 * gamme / saturé), quand l'IA dispose d'assez d'informations pour se prononcer.
 */
export default function MarketPositionCard({
  competitionLevel,
  averageMarketPrice,
  positioning,
  positioningExplanation,
}) {
  const competitionMeta = COMPETITION_META[competitionLevel] || COMPETITION_META.medium;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-2">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <LineChart size={16} /> Comparaison avec le marché
      </h3>
      <dl className="grid sm:grid-cols-3 gap-3">
        <div className="text-sm">
          <dt className="text-xs font-medium text-gray-500">Concurrence</dt>
          <dd className="font-semibold text-gray-800">
            {competitionMeta.emoji} {competitionMeta.label}
          </dd>
        </div>
        <div className="text-sm">
          <dt className="text-xs font-medium text-gray-500">Prix moyen</dt>
          <dd className="font-semibold text-gray-800">{averageMarketPrice || "Données insuffisantes."}</dd>
        </div>
        <div className="text-sm">
          <dt className="text-xs font-medium text-gray-500">Positionnement</dt>
          <dd className="font-semibold text-gray-800">
            {POSITIONING_LABELS[positioning] || POSITIONING_LABELS.unknown}
          </dd>
        </div>
      </dl>
      {positioningExplanation && <p className="text-sm text-gray-600">{positioningExplanation}</p>}
    </div>
  );
}
