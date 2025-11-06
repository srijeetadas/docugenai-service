from typing import List, Dict, Any
import re


class ComplianceChecker:
    """Check for PII, security, and compliance issues"""

    def __init__(self):
        self.sensitive_fields = {
            'critical': [
                'password', 'secret', 'token', 'apikey', 'api_key',
                'creditcard', 'credit_card', 'cvv', 'ssn',
                'social_security', 'socialsecuritynumber'
            ],
            'high': [
                'accountnumber', 'account_number', 'routingnumber',
                'passport', 'driverslicense', 'license'
            ],
            'medium': [
                'email', 'phone', 'address', 'dateofbirth', 'dob'
            ]
        }

    def check(self, spec: Dict[str, Any]) -> List[Dict]:
        """Check spec for compliance issues"""
        issues = []
        issue_id = 1

        # Check schemas
        schemas = spec.get('components', {}).get('schemas', {})

        for schema_name, schema in schemas.items():
            properties = schema.get('properties', {})

            for field_name, field_details in properties.items():
                severity = self._get_sensitivity_level(field_name)

                if severity:
                    # Check if field has proper documentation
                    description = field_details.get('description', '')

                    if not self._has_security_note(description, severity):
                        issues.append({
                            'id': issue_id,
                            'field': field_name,
                            'endpoint': f"Schema: {schema_name}",
                            'severity': severity,
                            'issue': self._get_issue_description(field_name, severity),
                            'suggestion': self._get_suggestion(field_name, severity)
                        })
                        issue_id += 1

        # Check endpoint parameters
        for path, methods in spec.get('paths', {}).items():
            for method, endpoint in methods.items():
                if method not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue

                # Check parameters
                for param in endpoint.get('parameters', []):
                    param_name = param.get('name', '')
                    severity = self._get_sensitivity_level(param_name)

                    if severity:
                        description = param.get('description', '')
                        if not self._has_security_note(description, severity):
                            issues.append({
                                'id': issue_id,
                                'field': param_name,
                                'endpoint': f"{method.upper()} {path}",
                                'severity': severity,
                                'issue': self._get_issue_description(param_name, severity),
                                'suggestion': self._get_suggestion(param_name, severity)
                            })
                            issue_id += 1

        return issues

    def _get_sensitivity_level(self, field_name: str) -> str:
        """Determine sensitivity level of a field"""
        field_lower = field_name.lower().replace('_', '').replace('-', '')

        for severity, keywords in self.sensitive_fields.items():
            for keyword in keywords:
                keyword_clean = keyword.replace('_', '')
                if keyword_clean in field_lower:
                    return severity

        return None

    def _has_security_note(self, description: str, severity: str) -> bool:
        """Check if description has appropriate security notes"""
        if not description:
            return False

        desc_lower = description.lower()

        # Check for security keywords
        security_keywords = [
            'mask', 'encrypt', 'hash', 'pii', 'sensitive',
            'permission', 'consent', 'gdpr', 'compliance',
            'tls', 'ssl', 'secure'
        ]

        return any(keyword in desc_lower for keyword in security_keywords)

    def _get_issue_description(self, field_name: str, severity: str) -> str:
        """Get description of the compliance issue"""
        if severity == 'critical':
            return f"Field '{field_name}' contains highly sensitive data and must include encryption and security notes"
        elif severity == 'high':
            return f"Field '{field_name}' may expose PII without proper masking or consent reference"
        else:
            return f"Field '{field_name}' contains personal data and should document privacy handling"

    def _get_suggestion(self, field_name: str, severity: str) -> str:
        """Get compliance suggestion"""
        field_lower = field_name.lower()

        if 'password' in field_lower or 'secret' in field_lower:
            return 'Add note: "Must be hashed using bcrypt. Never log or transmit in plain text. Minimum 12 characters with complexity requirements."'

        elif 'credit' in field_lower or 'card' in field_lower:
            return 'Add note: "Must be transmitted over TLS 1.3+. Encrypt using AES-256. PCI DSS Level 1 compliant. Never log or cache this field."'

        elif 'ssn' in field_lower or 'social' in field_lower:
            return 'Add note: "Requires explicit customer consent. Retained for 7 years per regulatory requirements. Automatically purged after retention period. Masked in all logs."'

        elif 'account' in field_lower:
            return 'Add note: "Masked for non-authorized users. Requires CUSTOMER_PII_READ permission. See data privacy policy for consent requirements."'

        elif 'email' in field_lower:
            return 'Add note: "Used for communication only. Requires opt-in consent. Users can update/delete via privacy portal. GDPR compliant."'

        else:
            return 'Add note: "Personal data. Requires appropriate permissions. See privacy policy for data handling procedures."'