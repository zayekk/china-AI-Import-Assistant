import React from "react";
import { ListChecks } from "lucide-react";

/**
 * "Pourquoi cette décision ?" : jusqu'à 5 raisons très courtes, affichées juste sous le
 * badge de décision principal (QuickSummaryBar), générées par l'IA à partir de constats
 * déjà présents ailleurs dans le rapport.
 */
export default function DecisionReasonsList({ reasons = [] }) {
  if (!reasons || reasons.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 sm:p-5">
      <h3 className="flex items-center gap-2 text-xs uppercase tracking-wide font-semibold text-gray-400 mb-2">
        <ListChecks size={14} /> Pourquoi cette décision ?
      </h3>
      <ul className="space-y-1">
        {reasons.map((reason, idx) => (
          <li key={idx} className="text-sm text-gray-800 flex items-center gap-2">
            <span className="text-green-600 font-bold">✓</span> {reason}
          </li>
        ))}
      </ul>
    </div>
  );
}
