import React from "react";
import { ShieldAlert } from "lucide-react";

/**
 * "Alertes importantes" : contradictions factuelles détectées par l'IA entre
 * différentes parties du texte source (titre vs specs, description vs avis,
 * capture vs capture...). Affichée avant le reste du rapport détaillé.
 */
export default function CriticalAlertsBanner({ alerts = [] }) {
  if (!alerts || alerts.length === 0) return null;

  return (
    <div className="bg-red-50 border-2 border-red-300 rounded-2xl p-4 sm:p-5">
      <h3 className="flex items-center gap-2 text-sm font-bold text-red-800 mb-2">
        <ShieldAlert size={18} /> Alertes importantes
      </h3>
      <ul className="space-y-1.5">
        {alerts.map((item, idx) => (
          <li key={idx} className="text-sm text-red-800 flex gap-2">
            <span className="font-bold">⚠</span> {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
