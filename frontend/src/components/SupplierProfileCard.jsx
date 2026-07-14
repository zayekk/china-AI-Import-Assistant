import React from "react";
import { Store } from "lucide-react";
import clsx from "clsx";

// Clés alignées sur supplier_profile.overall_trust côté serveur (contrat IA).
const TRUST_META = {
  low: { label: "Faible", classes: "bg-red-50 text-red-800 border-red-300" },
  medium: { label: "Moyenne", classes: "bg-orange-50 text-orange-800 border-orange-300" },
  high: { label: "Élevée", classes: "bg-green-50 text-green-800 border-green-300" },
};

const FIELDS = [
  ["estimated_age", "Ancienneté"],
  ["sales_volume", "Volume de ventes"],
  ["reputation", "Réputation"],
  ["service_quality", "Qualité de service"],
  ["shipping_speed", "Rapidité d'expédition"],
  ["return_policy", "Politique SAV"],
  ["dispute_history", "Historique des litiges"],
];

/**
 * Profil du vendeur estimé par l'IA à partir des captures boutique : ancienneté, volume de
 * ventes, réputation, service, et un badge de confiance globale.
 */
export default function SupplierProfileCard({ profile }) {
  if (!profile) return null;

  const trustMeta = TRUST_META[profile.overall_trust] || TRUST_META.medium;
  const entries = FIELDS.filter(([key]) => profile[key]);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-gray-800">
          <Store size={16} /> Profil du vendeur
        </h3>
        <span className={clsx("rounded-full border px-3 py-1 text-xs font-semibold", trustMeta.classes)}>
          Confiance globale : {trustMeta.label}
        </span>
      </div>
      {entries.length > 0 && (
        <dl className="grid sm:grid-cols-2 gap-3">
          {entries.map(([key, label]) => (
            <div key={key} className="text-sm">
              <dt className="text-xs font-medium text-gray-500">{label}</dt>
              <dd className="text-gray-800">{profile[key]}</dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}
