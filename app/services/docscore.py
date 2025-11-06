from typing import Dict, Any, List
from datetime import datetime

class DocScoreEngine:
    """Calculate and track documentation quality score."""

    def __init__(self):
        self.vague_terms = ["gets", "returns", "data", "info", "information", "stuff", "things", "object", "item"]
        self.min_description_length = 20
        self.history_store = {}

    def calculate(self, spec: Dict[str, Any], api_id: str = None) -> Dict[str, Any]:
        """Calculate documentation score."""
        score = 100
        issues = {"missing_descriptions": 0, "missing_examples": 0, "vague_descriptions": 0, "missing_error_responses": 0}

        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                desc = details.get("description", "")
                if not desc or len(desc) < self.min_description_length:
                    score -= 10; issues["missing_descriptions"] += 1
                elif self._is_vague(desc):
                    score -= 5; issues["vague_descriptions"] += 1

                if not self._has_examples(details):
                    score -= 5; issues["missing_examples"] += 1

                if not self._has_error_responses(details):
                    score -= 3; issues["missing_error_responses"] += 1

        score = max(0, score)
        potential_score = min(100, score + issues["missing_descriptions"] * 10 + issues["vague_descriptions"] * 5 + issues["missing_examples"] * 5)

        # Track timeline
        history = self.history_store.get(api_id, [])
        history.append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "score": score,
            "event": "Recalculated score",
            "projected": False
        })
        self.history_store[api_id] = history

        return {"score": score, "potential_score": potential_score, **issues, "history": history}

    def _is_vague(self, description: str) -> bool:
        return any(term in description.lower() for term in self.vague_terms)

    def _has_examples(self, endpoint: Dict) -> bool:
        rb = endpoint.get("requestBody", {})
        if rb:
            for details in rb.get("content", {}).values():
                if "example" in details or "examples" in details:
                    return True
        for resp in endpoint.get("responses", {}).values():
            for details in resp.get("content", {}).values():
                if "example" in details or "examples" in details:
                    return True
        return False

    def _has_error_responses(self, endpoint: Dict) -> bool:
        responses = endpoint.get("responses", {})
        return any(code in responses for code in ["400", "401", "404", "500"])
