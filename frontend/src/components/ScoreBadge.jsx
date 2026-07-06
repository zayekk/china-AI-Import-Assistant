import React from "react";
import clsx from "clsx";

/**
 * Affiche un score /100 sous forme de badge coloré selon le seuil.
 */
export default function ScoreBadge({ label, score }) {
  const numericScore = Number(score) || 0;

  const colorClass = clsx({
    "bg-green-100 text-green-700 border-green-300": numericScore >= 70,
    "bg-yellow-100 text-yellow-700 border-yellow-300":
      numericScore >= 40 && numericScore < 70,
    "bg-red-100 text-red-700 border-red-300": numericScore < 40,
  });

  return (
    <div className={clsx("rounded-xl border px-4 py-3 text-center", colorClass)}>
      <p className="text-2xl font-bold">{numericScore}</p>
      <p className="text-xs font-medium opacity-80 mt-1">{label}</p>
    </div>
  );
}
