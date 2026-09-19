import bisect

SIMPLE = {
    "breakpoints": [60, 70, 80, 90],
    "grades": ["F", "D", "C", "B", "A"],
}

PLUS_MINUS = {
    "breakpoints": [60, 63, 67, 70, 73, 77, 80, 83, 87, 90, 93, 97],
    "grades": ["F", "D-", "D", "D+", "C-", "C", "C+",
               "B-", "B", "B+", "A-", "A", "A+"],
}

PASS_FAIL = {
    "breakpoints": [60],
    "grades": ["Fail", "Pass"],
}

SCHEMES = {
    "simple": SIMPLE,
    "plus_minus": PLUS_MINUS,
    "pass_fail": PASS_FAIL,
}

DEFAULT_SCHEME_NAME = "simple"
DEFAULT_SCHEME = SCHEMES[DEFAULT_SCHEME_NAME]


def validate_scheme(scheme: dict) -> None:
    b, g = scheme["breakpoints"], scheme["grades"]
    if len(g) != len(b) + 1:
        raise ValueError(f"need {len(b)+1} grades, got {len(g)}")
    if b != sorted(b):
        raise ValueError("breakpoints must be sorted ascending")


# validate all schemes at import time
for _name, _scheme in SCHEMES.items():
    try:
        validate_scheme(_scheme)
    except ValueError as e:
        raise ValueError(f"Invalid scheme '{_name}': {e}")


def letter_grade(score: float, scheme: dict = DEFAULT_SCHEME) -> str:
    return scheme["grades"][bisect.bisect_right(scheme["breakpoints"], score)]


def weighted_score(scores: dict, weights: dict) -> float:
    return sum(scores.get(c, 0.0) * weights.get(c, 0.0) for c in weights)


def normalize_weights(weights: dict) -> dict:
    total = sum(weights.values())
    if total <= 0:
        return weights
    return {k: v / total for k, v in weights.items()}


def rank_students(students: list, weights: dict, scheme: dict | None = None) -> list:
    scheme = scheme or DEFAULT_SCHEME

    scored = []
    for s in students:
        scores = {k: v for k, v in s.items() if k not in ("nis", "name")}
        w = weighted_score(scores, weights)
        scored.append({
            "nis": s.get("nis", ""),
            "name": s.get("name", ""),
            "scores": scores,
            "weighted": w,
            "grade": letter_grade(w, scheme),
        })

    scored.sort(key=lambda r: r["weighted"], reverse=True)
    for i, r in enumerate(scored, start=1):
        r["rank"] = i
    return scored


def summary(results: list, scheme: dict = DEFAULT_SCHEME) -> dict:
    if not results:
        return {"average": 0.0, "passing": 0, "total": 0, "pass_rate": 0.0}

    fail_grade = scheme["grades"][0]
    scores = [r["weighted"] for r in results]
    passing = sum(1 for r in results if r["grade"] != fail_grade)

    return {
        "average": sum(scores) / len(scores),
        "passing": passing,
        "total": len(results),
        "pass_rate": passing / len(results),
    }
