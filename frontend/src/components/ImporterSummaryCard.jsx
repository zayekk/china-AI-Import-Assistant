import React from "react";
import { ClipboardCheck } from "lucide-react";

/**
 * Résumé final à destination de l'importateur : synthèse actionnable en quelques lignes,
 * pensée pour une lecture rapide avant décision.
 */
export default function ImporterSummaryCard({ lines = [] }) {
  if (!lines || lines.length === 0) return null;

  return (
    <div className="rounded-2xl border-2 border-indigo-300 bg-indigo-50 p-4 sm:p-5 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-indigo-900">
        <ClipboardCheck size={18} /> Résumé importateur
      </h3>
      <ol className="space-y-1.5 list-decimal list-inside">
        {lines.map((line, idx) => (
          <li key={idx} className="text-sm text-indigo-900">
            {line}
          </li>
        ))}
      </ol>
    </div>
  );
}
