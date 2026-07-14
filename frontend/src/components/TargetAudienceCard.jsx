import React from "react";
import { Users } from "lucide-react";

// Libellés (avec emoji) alignés sur les valeurs possibles de target_audiences côté serveur.
const AUDIENCE_LABELS = {
  students: "🎓 Étudiants",
  children: "🧒 Enfants",
  professionals: "💼 Professionnels",
  gamers: "🎮 Gamers",
  women: "👩 Femmes",
  men: "👨 Hommes",
  gifts: "🎁 Cadeaux",
  luxury: "💎 Luxe",
  daily_use: "🏠 Usage quotidien",
  other: "📦 Autre",
};

/**
 * Segments d'audience cible estimés par l'IA pour ce produit, sous forme de pills, avec
 * une courte explication du choix.
 */
export default function TargetAudienceCard({ audiences = [], explanation }) {
  if (!audiences || audiences.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
        <Users size={16} /> Ce produit convient à
      </h3>
      <div className="flex flex-wrap gap-2">
        {audiences.map((key) => (
          <span
            key={key}
            className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-700"
          >
            {AUDIENCE_LABELS[key] || key}
          </span>
        ))}
      </div>
      {explanation && <p className="text-sm text-gray-600">{explanation}</p>}
    </div>
  );
}
