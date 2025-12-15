"""Academic transcript template."""

import re
from typing import Any

from .base_template import BaseTemplate, DocumentCategory, FieldDefinition


class TranscriptTemplate(BaseTemplate):
    """Template for academic transcripts."""
    
    category = DocumentCategory.TRANSCRIPT
    
    @property
    def field_definitions(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="student_name",
                display_name="Student Name",
                field_type="string",
                required=True,
                description="Full name of the student",
            ),
            FieldDefinition(
                name="student_id",
                display_name="Student ID",
                field_type="string",
                required=False,
                description="Student identification number",
            ),
            FieldDefinition(
                name="institution_name",
                display_name="Institution Name",
                field_type="string",
                required=True,
                description="Name of the school/university",
            ),
            FieldDefinition(
                name="date_of_birth",
                display_name="Date of Birth",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="graduation_date",
                display_name="Graduation Date",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="gpa",
                display_name="GPA",
                field_type="number",
                required=False,
                description="Grade Point Average",
            ),
            FieldDefinition(
                name="gpa_scale",
                display_name="GPA Scale",
                field_type="string",
                required=False,
                description="GPA scale (e.g., 4.0, 10.0)",
            ),
            FieldDefinition(
                name="class_rank",
                display_name="Class Rank",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="total_credits",
                display_name="Total Credits",
                field_type="number",
                required=False,
            ),
            FieldDefinition(
                name="courses",
                display_name="Courses",
                field_type="array",
                required=False,
                description="List of courses with grades",
            ),
            FieldDefinition(
                name="degree_type",
                display_name="Degree Type",
                field_type="string",
                required=False,
                description="Type of degree (e.g., High School Diploma, Bachelor's)",
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "transcript",
            "academic record",
            "grade point average",
            "gpa",
            "credits",
            "course",
            "semester",
            "cumulative",
            "official transcript",
            "registrar",
        ]
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Clean and normalize transcript fields."""
        processed = fields.copy()
        
        # Normalize GPA
        if "gpa" in processed and processed["gpa"]:
            gpa_str = str(processed["gpa"])
            # Extract numeric GPA
            match = re.search(r'(\d+\.?\d*)', gpa_str)
            if match:
                processed["gpa"] = float(match.group(1))
        
        # Normalize student name (title case)
        if "student_name" in processed and processed["student_name"]:
            processed["student_name"] = processed["student_name"].strip().title()
        
        return processed
