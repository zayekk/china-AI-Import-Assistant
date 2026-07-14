import React from "react";
import { Smile, Frown, Star, AlertTriangle } from "lucide-react";
import clsx from "clsx";

// Clés alignées sur review_satisfaction côté serveur (contrat IA). Même forme que DEMAND_META
// (AnalysisResultCard.jsx) mais enum distinct (satisfaction des avis, pas demande marché).
const SATISFACTION_META = {
  very_high: { label: "Très forte", classes: "bg-green-50 text-green-800 border-green-300" },
  high: { label: "Forte", classes: "bg-lime-50 text-lime-700 border-lime-200" },
  medium: { label: "Moyenne", classes: "bg-yellow-50 text-yellow-700 border-yellow-200" },
  low: { label: "Faible", classes: "bg-orange-50 text-orange-700 border-orange-200" },
  very_low: { label: "Très faible", classes: "bg-red-50 text-red-800 border-red-300" },
};

/**
 * Synthèse des avis clients détectés par l'IA : points appréciés, problèmes fréquents,
 * satisfaction générale et défauts récurrents. Disparaît si aucun avis n'a été détecté.
 */
export default function ReviewsInsightCard({
  highlights = [],
  complaints = [],
  satisfaction,
  recurringDefects = [],
  available = false,
}) {
  if (!available) return null;
  if (highlights.length === 0 && complaints.length === 0 && recurringDefects.length === 0) {
    return null;
  }

  const satisfactionMeta = SATISFACTION_META[satisfaction];

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-800">Ce que disent réellement les clients</h3>

      {(highlights.length > 0 || complaints.length > 0) && (
        <div className="grid sm:grid-cols-2 gap-4">
          {highlights.length > 0 && (
            <div>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-green-700 mb-2">
                <Smile size={16} /> Points appréciés
              </h4>
              <ul className="space-y-1.5">
                {highlights.map((item, idx) => (
                  <li key={idx} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-green-600">✔</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {complaints.length > 0 && (
            <div>
              <h4 className="flex items-center gap-2 text-sm font-semibold text-red-700 mb-2">
                <Frown size={16} /> Problèmes fréquents
              </h4>
              <ul className="space-y-1.5">
                {complaints.map((item, idx) => (
                  <li key={idx} className="text-sm text-gray-700 flex gap-2">
                    <span className="text-red-600">✖</span> {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {satisfactionMeta && (
        <div className="flex items-center justify-between flex-wrap gap-2 border-t border-gray-100 pt-3">
          <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
            <Star size={16} /> Satisfaction générale
          </span>
          <span className={clsx("rounded-full border px-3 py-1 text-xs font-semibold", satisfactionMeta.classes)}>
            {satisfactionMeta.label}
          </span>
        </div>
      )}

      {recurringDefects.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-3">
          <h4 className="flex items-center gap-2 text-sm font-semibold text-orange-800 mb-2">
            <AlertTriangle size={16} /> Défauts récurrents
          </h4>
          <ul className="space-y-1.5">
            {recurringDefects.map((item, idx) => (
              <li key={idx} className="text-sm text-orange-800">
                • {item}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
