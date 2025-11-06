import yaml
import json
from typing import Dict, Any, Optional


class OpenAPIParser:
    """Parse and validate OpenAPI specifications"""

    def parse(self, content: str) -> Dict[str, Any]:
        """Parse YAML or JSON OpenAPI spec"""
        try:
            # Try YAML first
            spec = yaml.safe_load(content)
            return spec
        except yaml.YAMLError:
            # Try JSON
            try:
                spec = json.loads(content)
                return spec
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid OpenAPI spec format: {e}")

    def validate(self, spec: Dict[str, Any]) -> bool:
        """Basic validation of OpenAPI structure"""
        required_fields = ['openapi', 'info', 'paths']
        return all(field in spec for field in required_fields)

    def extract_endpoints(self, spec: Dict[str, Any]) -> list:
        """Extract all endpoints from spec"""
        endpoints = []

        for path, methods in spec.get('paths', {}).items():
            for method, details in methods.items():
                if method in ['get', 'post', 'put', 'delete', 'patch']:
                    endpoints.append({
                        'path': path,
                        'method': method.upper(),
                        'summary': details.get('summary', ''),
                        'description': details.get('description', ''),
                        'parameters': details.get('parameters', []),
                        'requestBody': details.get('requestBody'),
                        'responses': details.get('responses', {}),
                    })

        return endpoints

    def extract_schemas(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """Extract schemas from components"""
        return spec.get('components', {}).get('schemas', {})