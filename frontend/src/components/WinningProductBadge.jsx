import React from "react";
import { Flame } from "lucide-react";
import clsx from "clsx";

function scoreClasses(score) {
  if (score >= 7) return "bg-green-50 text-green-800 border-green-300";
  if (score >= 4) return "bg-yellow-50 text-yellow-800 border-yellow-300";
  return "bg-red-50 text-red-800 border-red-300";
}

/**
 * "Winning Product" : potentiel produit gagnant noté sur 10, généré par l'IA (demande, marge,
 * concurrence, prix, originalité, risques) — plafonné côté serveur à 3/10 si une alerte
 * critique existe (voir _WINNING_SCORE_CAP_WITH_CRITICAL_ALERTS côté backend).
 */
export default function WinningProductBadge({ score = 0, explanation }) {
  return (
    <div className={clsx("rounded-2xl border-2 p-4 sm:p-5", scoreClasses(score))}>
      <div className="flex items-center gap-3">
        <Flame size={22} className="shrink-0" />
        <div>
          <p className="text-xs uppercase tracking-wide font-medium opacity-70">Winning Product</p>
          <p className="text-lg font-bold">🔥 {score}/10</p>
        </div>
      </div>
      {explanation && <p className="text-sm mt-2">{explanation}</p>}
    </div>
  );
}
