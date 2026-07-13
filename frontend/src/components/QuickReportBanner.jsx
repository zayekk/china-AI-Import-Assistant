import React from "react";
import { Zap } from "lucide-react";

/**
 * "Rapport rapide" : résumé lisible en moins de 10 secondes (liste de courtes lignes
 * préfixées d'emoji, générées par l'IA à partir des champs déjà couverts ailleurs dans
 * le rapport — voir la règle prompt correspondante).
 */
export default function QuickReportBanner({ items = [] }) {
  if (!items || items.length === 0) return null;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 sm:p-5">
      <h3 className="flex items-center gap-2 text-xs uppercase tracking-wide font-semibold text-gray-400 mb-2">
        <Zap size={14} /> Rapport rapide
      </h3>
      <ul className="space-y-1">
        {items.map((item, idx) => (
          <li key={idx} className="text-sm font-medium text-gray-800">
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
