"""ID document template (passport, driver's license, ID card)."""

import re
from typing import Any

from .base_template import BaseTemplate, DocumentCategory, FieldDefinition


class IDDocumentTemplate(BaseTemplate):
    """Template for identity documents."""
    
    category = DocumentCategory.ID_DOCUMENT
    
    @property
    def field_definitions(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="full_name",
                display_name="Full Name",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                name="first_name",
                display_name="First Name",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="last_name",
                display_name="Last Name",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="date_of_birth",
                display_name="Date of Birth",
                field_type="date",
                required=True,
            ),
            FieldDefinition(
                name="document_number",
                display_name="Document Number",
                field_type="string",
                required=True,
                description="ID number, passport number, etc.",
            ),
            FieldDefinition(
                name="document_type",
                display_name="Document Type",
                field_type="string",
                required=False,
                description="Passport, Driver's License, National ID, etc.",
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
                name="nationality",
                display_name="Nationality",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="gender",
                display_name="Gender",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="address",
                display_name="Address",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="place_of_birth",
                display_name="Place of Birth",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="issuing_authority",
                display_name="Issuing Authority",
                field_type="string",
                required=False,
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "passport",
            "driver",
            "license",
            "identity",
            "id card",
            "national id",
            "date of birth",
            "dob",
            "expiry",
            "nationality",
            "place of issue",
        ]
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize ID fields."""
        processed = fields.copy()
        
        # If full_name is not set but first/last are, combine them
        if not processed.get("full_name"):
            first = processed.get("first_name", "")
            last = processed.get("last_name", "")
            if first or last:
                processed["full_name"] = f"{first} {last}".strip()
        
        # Normalize names
        for name_field in ["full_name", "first_name", "last_name"]:
            if name_field in processed and processed[name_field]:
                processed[name_field] = processed[name_field].strip().title()
        
        # Normalize gender
        if "gender" in processed and processed["gender"]:
            gender = str(processed["gender"]).upper().strip()
            if gender in ("M", "MALE"):
                processed["gender"] = "Male"
            elif gender in ("F", "FEMALE"):
                processed["gender"] = "Female"
        
        return processed
