import React from "react";
import { Star } from "lucide-react";

/**
 * Affiche une note sur 5 étoiles (potentiel commercial IA).
 */
export default function StarRating({ rating = 0, max = 5 }) {
  return (
    <div className="flex items-center gap-0.5" aria-label={`${rating}/${max}`}>
      {Array.from({ length: max }).map((_, i) => (
        <Star
          key={i}
          size={18}
          className={i < rating ? "fill-amber-400 text-amber-400" : "text-gray-300"}
        />
      ))}
    </div>
  );
}
