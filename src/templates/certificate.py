"""Certificate template (achievement, completion, award)."""

from typing import Any

from .base_template import BaseTemplate, DocumentCategory, FieldDefinition


class CertificateTemplate(BaseTemplate):
    """Template for certificates and awards."""
    
    category = DocumentCategory.CERTIFICATE
    
    @property
    def field_definitions(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="recipient_name",
                display_name="Recipient Name",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                name="certificate_title",
                display_name="Certificate Title",
                field_type="string",
                required=True,
                description="Title or type of certificate",
            ),
            FieldDefinition(
                name="issuing_organization",
                display_name="Issuing Organization",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                name="issue_date",
                display_name="Issue Date",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="expiry_date",
                display_name="Expiry Date",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="certificate_id",
                display_name="Certificate ID",
                field_type="string",
                required=False,
                description="Certificate number or credential ID",
            ),
            FieldDefinition(
                name="achievement_description",
                display_name="Achievement Description",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="course_name",
                display_name="Course/Program Name",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="grade_or_score",
                display_name="Grade/Score",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="duration",
                display_name="Duration",
                field_type="string",
                required=False,
                description="Duration of course or validity period",
            ),
            FieldDefinition(
                name="signatories",
                display_name="Signatories",
                field_type="array",
                required=False,
                description="Names of people who signed the certificate",
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "certificate",
            "certify",
            "certification",
            "awarded",
            "achievement",
            "completion",
            "hereby",
            "credential",
            "honor",
            "recognition",
            "conferred",
        ]
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize certificate fields."""
        processed = fields.copy()
        
        # Normalize recipient name
        if "recipient_name" in processed and processed["recipient_name"]:
            processed["recipient_name"] = processed["recipient_name"].strip().title()
        
        # Clean up certificate title
        if "certificate_title" in processed and processed["certificate_title"]:
            title = processed["certificate_title"].strip()
            # Remove common prefixes
            for prefix in ["Certificate of ", "Certificate for "]:
                if title.lower().startswith(prefix.lower()):
                    title = title[len(prefix):]
            processed["certificate_title"] = title
        
        return processed
