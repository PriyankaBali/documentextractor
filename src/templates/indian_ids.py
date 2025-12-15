"""Indian ID document templates (Aadhaar, PAN, UAN, Voter ID, Driving License)."""

from typing import Any

from .base_template import BaseTemplate, DocumentCategory, FieldDefinition


class AadhaarCardTemplate(BaseTemplate):
    """Template for Aadhaar Card (UIDAI)."""
    
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
                name="aadhaar_number",
                display_name="Aadhaar Number",
                field_type="string",
                required=True,
                description="12-digit Aadhaar number (XXXX XXXX XXXX)",
            ),
            FieldDefinition(
                name="date_of_birth",
                display_name="Date of Birth",
                field_type="date",
                required=True,
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
                name="pincode",
                display_name="PIN Code",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="vid",
                display_name="Virtual ID (VID)",
                field_type="string",
                required=False,
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "aadhaar",
            "uidai",
            "unique identification",
            "भारत सरकार",
            "government of india",
            "enrolment",
            "vid",
            "आधार",
        ]
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        processed = fields.copy()
        
        # Format Aadhaar number with spaces
        if "aadhaar_number" in processed and processed["aadhaar_number"]:
            aadhaar = str(processed["aadhaar_number"]).replace(" ", "").replace("-", "")
            if len(aadhaar) == 12 and aadhaar.isdigit():
                processed["aadhaar_number"] = f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:]}"
        
        # Normalize gender
        if "gender" in processed and processed["gender"]:
            gender = str(processed["gender"]).upper().strip()
            if gender in ("M", "MALE", "पुरुष"):
                processed["gender"] = "Male"
            elif gender in ("F", "FEMALE", "महिला"):
                processed["gender"] = "Female"
        
        return processed


class PANCardTemplate(BaseTemplate):
    """Template for PAN Card (Income Tax)."""
    
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
                name="pan_number",
                display_name="PAN Number",
                field_type="string",
                required=True,
                description="10-character PAN (e.g., ABCDE1234F)",
            ),
            FieldDefinition(
                name="fathers_name",
                display_name="Father's Name",
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
                name="signature_name",
                display_name="Name on Signature",
                field_type="string",
                required=False,
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "permanent account number",
            "pan",
            "income tax",
            "आयकर विभाग",
            "govt. of india",
            "NSDL",
            "UTI",
        ]
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        processed = fields.copy()
        
        # Uppercase PAN number
        if "pan_number" in processed and processed["pan_number"]:
            processed["pan_number"] = str(processed["pan_number"]).upper().strip()
        
        return processed


class UANCardTemplate(BaseTemplate):
    """Template for UAN Card / Shram Card (EPFO)."""
    
    category = DocumentCategory.ID_DOCUMENT
    
    @property
    def field_definitions(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="member_name",
                display_name="Member Name",
                field_type="string",
                required=True,
                description="Name of the member/employee",
            ),
            FieldDefinition(
                name="uan_number",
                display_name="UAN Number",
                field_type="string",
                required=True,
                description="12-digit Universal Account Number",
            ),
            FieldDefinition(
                name="date_of_birth",
                display_name="Date of Birth",
                field_type="date",
                required=True,
            ),
            FieldDefinition(
                name="gender",
                display_name="Gender",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="fathers_name",
                display_name="Father's/Husband's Name",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="aadhaar_verified",
                display_name="Aadhaar Verified",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="pan_verified",
                display_name="PAN Verified", 
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="bank_verified",
                display_name="Bank Verified",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="employer_name",
                display_name="Employer Name",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="establishment_id",
                display_name="Establishment ID",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="address",
                display_name="Address",
                field_type="string",
                required=False,
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "uan",
            "universal account number",
            "epfo",
            "epf",
            "provident fund",
            "shram",
            "e-shram",
            "ministry of labour",
            "श्रम कार्ड",
            "member id",
            "unorganised worker",
        ]
    
    def post_process(self, fields: dict[str, Any]) -> dict[str, Any]:
        processed = fields.copy()
        
        # Normalize name
        if "member_name" in processed and processed["member_name"]:
            processed["member_name"] = processed["member_name"].strip().title()
        
        # Format UAN
        if "uan_number" in processed and processed["uan_number"]:
            uan = str(processed["uan_number"]).replace(" ", "").replace("-", "")
            if uan.isdigit():
                processed["uan_number"] = uan
        
        return processed


class VoterIDTemplate(BaseTemplate):
    """Template for Voter ID Card (EPIC)."""
    
    category = DocumentCategory.ID_DOCUMENT
    
    @property
    def field_definitions(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="elector_name",
                display_name="Elector's Name",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                name="epic_number",
                display_name="EPIC Number",
                field_type="string",
                required=True,
                description="Voter ID number",
            ),
            FieldDefinition(
                name="fathers_name",
                display_name="Father's/Husband's Name",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="date_of_birth",
                display_name="Date of Birth",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="age",
                display_name="Age",
                field_type="number",
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
                name="polling_station",
                display_name="Polling Station",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="constituency",
                display_name="Assembly Constituency",
                field_type="string",
                required=False,
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "voter",
            "epic",
            "election commission",
            "elector",
            "polling",
            "निर्वाचन",
            "मतदाता",
            "assembly constituency",
        ]


class DrivingLicenseTemplate(BaseTemplate):
    """Template for Indian Driving License."""
    
    category = DocumentCategory.ID_DOCUMENT
    
    @property
    def field_definitions(self) -> list[FieldDefinition]:
        return [
            FieldDefinition(
                name="holder_name",
                display_name="Name of Holder",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                name="license_number",
                display_name="License Number",
                field_type="string",
                required=True,
            ),
            FieldDefinition(
                name="date_of_birth",
                display_name="Date of Birth",
                field_type="date",
                required=True,
            ),
            FieldDefinition(
                name="blood_group",
                display_name="Blood Group",
                field_type="string",
                required=False,
            ),
            FieldDefinition(
                name="fathers_name",
                display_name="Father's/Husband's Name",
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
                name="issue_date",
                display_name="Date of Issue",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="valid_till",
                display_name="Valid Till",
                field_type="date",
                required=False,
            ),
            FieldDefinition(
                name="vehicle_classes",
                display_name="Vehicle Class(es)",
                field_type="string",
                required=False,
                description="e.g., LMV, MCWG",
            ),
            FieldDefinition(
                name="issuing_authority",
                display_name="Issuing Authority (RTO)",
                field_type="string",
                required=False,
            ),
        ]
    
    @property
    def classification_keywords(self) -> list[str]:
        return [
            "driving",
            "license",
            "licence",
            "motor vehicle",
            "rto",
            "transport",
            "lmv",
            "mcwg",
            "valid till",
            "blood group",
        ]
