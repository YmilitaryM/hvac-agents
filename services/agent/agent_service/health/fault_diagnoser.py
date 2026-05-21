import math


def diagnose(symptoms: dict, fmea_db: list[dict], top_n: int = 3) -> list[dict]:
    """
    Match symptom signature against FMEA knowledge base using cosine similarity.
    Returns top-N matches with confidence scores.
    """
    results = []
    sym_keys = set(symptoms.keys())
    sym_values = {k: float(v) if isinstance(v, (int, float)) else (1.0 if v else 0.0) for k, v in symptoms.items()}

    for record in fmea_db:
        rec_symptoms = record.get("symptoms", {})
        if not rec_symptoms:
            continue

        rec_keys = set(rec_symptoms.keys())
        common_keys = sym_keys & rec_keys

        if not common_keys:
            continue

        dot = sum(sym_values.get(k, 0) * float(rec_symptoms.get(k, 0)) for k in common_keys)
        norm_s = math.sqrt(sum(v ** 2 for v in sym_values.values()))
        norm_r = math.sqrt(sum(float(v) ** 2 for v in rec_symptoms.values()))

        similarity = dot / (norm_s * norm_r) if norm_s > 0 and norm_r > 0 else 0

        results.append({
            "fmea_id": record["id"],
            "failure_mode": record["failure_mode"],
            "confidence": round(similarity, 3),
        })

    results.sort(key=lambda x: x["confidence"], reverse=True)
    return results[:top_n]
