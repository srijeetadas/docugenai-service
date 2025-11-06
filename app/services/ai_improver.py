from openai import OpenAI
from typing import List, Dict, Any
import json
import time


class AIImprover:
    """
    AI-powered engine to improve API documentation quality.
    Generates better descriptions and examples using OpenAI.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_improvements(self, spec: Dict[str, Any]) -> List[Dict]:
        """Generate improvements for all problematic endpoints."""
        improvements = []
        improvement_id = 1  # start assigning IDs

        for path, methods in spec.get("paths", {}).items():
            for method, endpoint in methods.items():
                if method not in ["get", "post", "put", "delete", "patch"]:
                    continue

                description = endpoint.get("description", "")

                # Missing or vague description
                if not description or len(description) < 20 or self._is_vague(description):
                    improved = self._improve_description(
                        method, path, description,
                        endpoint.get("parameters", []),
                        endpoint.get("responses", {})
                    )

                    if improved:
                        improvements.append({
                            "id": improvement_id,
                            "endpoint": f"{method.upper()} {path}",
                            "field": "description",
                            "before": description or "No description provided",
                            "after": improved,
                            "reason": self._get_reason(description),
                            "priority": "high" if not description else "medium"
                        })
                        improvement_id += 1

                # Missing examples
                if not self._has_examples(endpoint):
                    example = self._generate_example(method, path, endpoint)
                    if example:
                        improvements.append({
                            "id": improvement_id,
                            "endpoint": f"{method.upper()} {path}",
                            "field": "example",
                            "before": "No example provided",
                            "after": json.dumps(example, indent=2),
                            "reason": "Missing request/response example",
                            "priority": "high"
                        })
                        improvement_id += 1

        return improvements

    # ======================================================
    # 🧩 INTERNAL HELPERS
    # ======================================================
    def _improve_description(
        self,
        method: str,
        path: str,
        current_desc: str,
        parameters: List,
        responses: Dict
    ) -> str:
        """Use AI to rewrite and improve endpoint description."""
        prompt = f"""
Improve this API endpoint description to be clear, detailed, and professional.

Endpoint: {method.upper()} {path}
Current description: {current_desc if current_desc else 'None'}
Parameters: {json.dumps(parameters, indent=2) if parameters else 'None'}
Response codes: {list(responses.keys()) if responses else 'None'}

Requirements:
1. Explain what the endpoint does.
2. Describe input and output data briefly.
3. Mention key parameters or responses if relevant.
4. Keep it concise (2–3 sentences).
5. Use professional tone.

Respond ONLY with the improved description (no quotes, no explanations).
"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert API documentation writer."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"⚠️ Error improving description for {path}: {e}")
            return None

    def _generate_example(self, method: str, path: str, endpoint: Dict) -> Dict:
        """Use AI to generate realistic JSON examples for an API endpoint."""
        prompt = f"""
Generate a realistic example JSON payload for this API endpoint.

Endpoint: {method.upper()} {path}
Description: {endpoint.get('description', 'Not provided')}

Rules:
- Respond with ONLY valid JSON (no markdown, no comments, no explanations).
- The JSON must reflect a typical request or response for this endpoint.
- If uncertain, return an empty JSON object {{}}.
"""

        for attempt in range(2):  # Retry once if invalid JSON
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert API documentation writer. Output must be valid JSON only."
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                    max_tokens=300,
                )

                raw_output = response.choices[0].message.content.strip()
                cleaned_output = (
                    raw_output.strip()
                    .replace("```json", "")
                    .replace("```", "")
                    .strip()
                )

                return json.loads(cleaned_output)
            except json.JSONDecodeError:
                print(f"⚠️ Attempt {attempt + 1}: Invalid JSON from model at {path}. Retrying...")
                print("Raw output:\n", raw_output)
                time.sleep(1)
                continue
            except Exception as e:
                print(f"⚠️ Error generating example for {path}: {e}")
                return None

        print(f"❌ Failed to generate valid JSON example for {path} after retries.")
        return None

    # ======================================================
    # 🔍 UTILITIES
    # ======================================================
    def _is_vague(self, description: str) -> bool:
        """Check if a description is vague."""
        vague_terms = ["gets", "returns", "data", "info", "stuff", "fetches"]
        return any(term in description.lower() for term in vague_terms)

    def _has_examples(self, endpoint: Dict) -> bool:
        """Check if endpoint already has request/response examples."""
        request_body = endpoint.get("requestBody", {})
        if request_body:
            content = request_body.get("content", {})
            for details in content.values():
                if "example" in details or "examples" in details:
                    return True
        responses = endpoint.get("responses", {})
        for resp in responses.values():
            content = resp.get("content", {})
            for details in content.values():
                if "example" in details or "examples" in details:
                    return True
        return False

    def _get_reason(self, description: str) -> str:
        """Explain why a description needs improvement."""
        if not description:
            return "Missing description – endpoint purpose unclear."
        elif len(description) < 20:
            return "Description too brief and lacks details."
        else:
            return "Description uses vague language – needs more specificity."
