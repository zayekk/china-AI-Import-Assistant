import React from "react";
import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import clsx from "clsx";

const CONFIG = {
  BUY: {
    icon: CheckCircle2,
    label: "Achat recommandé",
    classes: "bg-green-50 text-green-800 border-green-300",
  },
  CAUTION: {
    icon: AlertTriangle,
    label: "Prudence requise",
    classes: "bg-yellow-50 text-yellow-800 border-yellow-300",
  },
  AVOID: {
    icon: XCircle,
    label: "À éviter",
    classes: "bg-red-50 text-red-800 border-red-300",
  },
};

export default function RecommendationBanner({ recommendation }) {
  const config = CONFIG[recommendation] || CONFIG.CAUTION;
  const Icon = config.icon;

  return (
    <div
      className={clsx(
        "flex items-center gap-3 rounded-xl border px-4 py-3 font-semibold",
        config.classes
      )}
    >
      <Icon size={22} />
      <span>{config.label}</span>
    </div>
  );
}
