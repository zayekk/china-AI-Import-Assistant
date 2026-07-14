import React from "react";
import { Rocket } from "lucide-react";

const FIELD_LABELS = [
  ["suggestedQuantity", "Quantité de départ conseillée"],
  ["quantityReason", "Pourquoi"],
  ["salesTips", "Conseils de vente"],
  ["launchStrategy", "Stratégie de lancement"],
];

/**
 * Conseils d'importation générés par l'IA : quantité de départ conseillée, conseils de
 * vente et stratégie de lancement. Disparaît si aucun conseil n'a été généré.
 */
export default function ImportStrategyCard({
  suggestedQuantity,
  quantityReason,
  salesTips,
  launchStrategy,
}) {
  const values = { suggestedQuantity, quantityReason, salesTips, launchStrategy };
  const entries = FIELD_LABELS.filter(([key]) => values[key]);

  if (entries.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Rocket size={16} /> Conseil d'importation
      </h3>
      <dl className="space-y-2.5">
        {entries.map(([key, label]) => (
          <div key={key} className="text-sm">
            <dt className="text-xs font-medium text-gray-500">{label}</dt>
            <dd className="text-gray-700">{values[key]}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
