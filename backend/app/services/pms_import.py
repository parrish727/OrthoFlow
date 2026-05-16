"""Dentrix/Eaglesoft file import — parse CSV/XML exports into OrthoFlow data."""
import csv
import io
import xml.etree.ElementTree as ET


def parse_dentrix_csv(content: bytes) -> dict:
    """Parse Dentrix patient/financial export CSV."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    patients = []
    for row in reader:
        patients.append({
            "patient_id": row.get("PatientID", row.get("Patient ID", "")),
            "last_name": row.get("LastName", row.get("Last Name", "")),
            "first_name": row.get("FirstName", row.get("First Name", "")),
            "treatment_type": row.get("TreatmentType", row.get("Treatment", "")),
            "insurance": row.get("Insurance", row.get("Carrier", "")),
            "balance": float(row.get("Balance", row.get("PatientBalance", "0")) or 0),
        })
    return {"source": "dentrix", "patients": patients, "count": len(patients)}


def parse_eaglesoft_csv(content: bytes) -> dict:
    """Parse Eaglesoft patient/financial export CSV."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    patients = []
    for row in reader:
        patients.append({
            "patient_id": row.get("PatNum", row.get("Patient #", "")),
            "last_name": row.get("LName", row.get("Last", "")),
            "first_name": row.get("FName", row.get("First", "")),
            "treatment_type": row.get("ProcCode", row.get("Procedure", "")),
            "insurance": row.get("CarrierName", row.get("Insurance", "")),
            "balance": float(row.get("PatBal", row.get("Balance", "0")) or 0),
        })
    return {"source": "eaglesoft", "patients": patients, "count": len(patients)}


def parse_xml_export(content: bytes) -> dict:
    """Parse generic XML export from Dentrix/Eaglesoft."""
    root = ET.fromstring(content)
    patients = []
    for patient in root.findall(".//Patient") or root.findall(".//patient") or root.findall(".//Record"):
        patients.append({
            "patient_id": patient.findtext("ID", patient.findtext("PatientID", "")),
            "last_name": patient.findtext("LastName", patient.findtext("LName", "")),
            "first_name": patient.findtext("FirstName", patient.findtext("FName", "")),
            "treatment_type": patient.findtext("Treatment", patient.findtext("ProcCode", "")),
            "insurance": patient.findtext("Insurance", patient.findtext("Carrier", "")),
            "balance": float(patient.findtext("Balance", "0") or 0),
        })
    return {"source": "xml", "patients": patients, "count": len(patients)}


def parse_file(content: bytes, filename: str) -> dict:
    """Auto-detect format and parse."""
    lower = filename.lower()
    if lower.endswith(".xml"):
        return parse_xml_export(content)
    # Try CSV (works for both Dentrix and Eaglesoft)
    text = content.decode("utf-8", errors="replace")
    if "PatientID" in text or "Patient ID" in text or "LastName" in text:
        return parse_dentrix_csv(content)
    if "PatNum" in text or "LName" in text or "CarrierName" in text:
        return parse_eaglesoft_csv(content)
    # Generic CSV fallback
    return parse_dentrix_csv(content)
