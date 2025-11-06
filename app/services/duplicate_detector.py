from openai import OpenAI
import numpy as np
from typing import List, Dict, Any


class DuplicateDetector:
    """Detect duplicate/similar APIs using embeddings"""

    def __init__(self, api_key: str, embedding_model: str = "text-embedding-3-small"):
        self.client = OpenAI(api_key=api_key)
        self.embedding_model = embedding_model
        self.threshold = 0.70  # 70% similarity

    def find_duplicates(self, spec: Dict[str, Any],
                        existing_apis: List[Dict[str, Any]]) -> List[Dict]:
        """Find similar APIs in existing collection"""
        # Generate embedding for current API
        current_summary = self._summarize_api(spec)
        current_embedding = self._generate_embedding(current_summary)

        duplicates = []

        for existing_api in existing_apis:
            # Skip if it's the same API
            if existing_api.get('name') == spec.get('info', {}).get('title'):
                continue

            # Get or generate embedding for existing API
            if 'embedding' in existing_api:
                existing_embedding = np.array(existing_api['embedding'])
            else:
                existing_summary = self._summarize_api(existing_api['spec'])
                existing_embedding = self._generate_embedding(existing_summary)

            # Calculate similarity (manual cosine similarity)
            similarity = self._cosine_similarity(current_embedding, existing_embedding)

            if similarity >= self.threshold:
                overlap_percentage = int(similarity * 100)
                overlapping_endpoints = self._count_overlapping_endpoints(
                    spec, existing_api['spec']
                )

                duplicates.append({
                    'name': existing_api['name'],
                    'api_id': existing_api['id'],
                    'overlap': overlap_percentage,
                    'endpoints': overlapping_endpoints,
                    'recommendation': self._generate_recommendation(
                        overlap_percentage,
                        spec.get('info', {}).get('title'),
                        existing_api['name']
                    ),
                    'details': self._get_overlap_details(spec, existing_api['spec'])
                })

        # Sort by overlap percentage (highest first)
        duplicates.sort(key=lambda x: x['overlap'], reverse=True)

        return duplicates

    def _summarize_api(self, spec: Dict[str, Any]) -> str:
        """Create text summary of API for embedding"""
        parts = []

        # API info
        info = spec.get('info', {})
        parts.append(info.get('title', ''))
        parts.append(info.get('description', ''))

        # All endpoints
        for path, methods in spec.get('paths', {}).items():
            parts.append(path)
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    parts.append(details.get('summary', ''))
                    parts.append(details.get('description', ''))

        return ' '.join(filter(None, parts))

    def _generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding vector for text"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return np.array(response.data[0].embedding)
        except Exception as e:
            print(f"Error generating embedding: {e}")
            return np.zeros(1536)  # Return zero vector on error

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity manually (no sklearn needed)"""
        # Cosine similarity = dot product / (norm1 * norm2)
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    def _count_overlapping_endpoints(self, spec1: Dict, spec2: Dict) -> int:
        """Count number of similar endpoints"""
        paths1 = set(spec1.get('paths', {}).keys())
        paths2 = set(spec2.get('paths', {}).keys())

        # Exact matches
        exact_matches = len(paths1 & paths2)

        # Fuzzy matches (similar paths)
        fuzzy_matches = 0
        for p1 in paths1:
            for p2 in paths2:
                if self._paths_similar(p1, p2) and p1 not in paths2:
                    fuzzy_matches += 1
                    break

        return exact_matches + fuzzy_matches

    def _paths_similar(self, path1: str, path2: str) -> bool:
        """Check if two paths are similar"""
        # Remove path parameters for comparison
        p1_clean = path1.replace('{', '').replace('}', '').replace('id', '').replace('_', '')
        p2_clean = path2.replace('{', '').replace('}', '').replace('id', '').replace('_', '')

        # Simple similarity check
        return p1_clean.lower() in p2_clean.lower() or p2_clean.lower() in p1_clean.lower()

    def _generate_recommendation(self, overlap: int, api1_name: str,
                                 api2_name: str) -> str:
        """Generate consolidation recommendation"""
        if overlap >= 85:
            return f"High overlap detected. Consider deprecating {api2_name} and migrating consumers to {api1_name}"
        elif overlap >= 70:
            return f"Moderate overlap. Consider consolidating overlapping functionality"
        else:
            return f"Some similarity detected. Review for potential alignment"

    def _get_overlap_details(self, spec1: Dict, spec2: Dict) -> List[str]:
        """Get specific details about what overlaps"""
        details = []

        paths1 = set(spec1.get('paths', {}).keys())
        paths2 = set(spec2.get('paths', {}).keys())
        common_paths = paths1 & paths2

        if common_paths:
            details.append(f"Both expose {len(common_paths)} identical endpoints")

        # Check schemas
        schemas1 = set(spec1.get('components', {}).get('schemas', {}).keys())
        schemas2 = set(spec2.get('components', {}).get('schemas', {}).keys())
        common_schemas = schemas1 & schemas2

        if common_schemas:
            details.append(f"Share {len(common_schemas)} common data models")

        return details if details else ["Similar API functionality"]