import React from "react";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Paramètres</h1>
        <p className="text-gray-500 mt-1">Gestion du compte et préférences.</p>
      </div>

      <div className="bg-white rounded-2xl border border-gray-200 p-6 text-sm text-gray-500">
        Cette section sera enrichie lors de l'évolution du projet en SaaS complet
        (gestion d'abonnement, quotas d'analyses, clés API personnelles, etc.).
      </div>
    </div>
  );
}
