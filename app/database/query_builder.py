"""
Query Builder for CDWWORK Database
Constructs optimized queries for note extraction and specialty identification
"""

from typing import List, Optional, Dict, Any
from datetime import datetime


class CDWWorkQueryBuilder:
    """Builds SQL queries for CDWWORK database operations."""
    
    # Verified table names
    NOTE_TEXT_TABLE = "[CDWWork].[STIUNotes].[TIUDocument_8925]"
    NOTE_METADATA_TABLE = "[CDWWork].[TIU].[TIUDocument]"
    NOTE_DEFINITION_TABLE = "[CDWWork].[Dim].[TIUDocumentDefinition]"
    TREATING_SPECIALTY_TABLE = "[CDWWork].[Dim].[TreatingSpecialty]"
    SPECIALTY_TRANSFER_TABLE = "[CDWWork].[Inpat].[SpecialtyTransfer]"
    INPATIENT_TABLE = "[CDWWork].[Inpat].[Inpatient]"
    
    @staticmethod
    def get_notes_by_patient(
        patient_sid: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        note_title_filter: Optional[List[str]] = None,
        limit: int = 100
    ) -> str:
        """
        Build query to get notes for a specific patient.
        
        Args:
            patient_sid: Patient identifier
            start_date: Optional start date filter
            end_date: Optional end date filter
            note_title_filter: Optional list of note title patterns
            limit: Maximum number of notes to return
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT TOP {limit}
            doc.TIUDocumentSID,
            doc.PatientSID,
            doc.VisitSID,
            doc.ReferenceDateTime AS NoteDateTime,
            doc.SignatureDateTime,
            doc.CosignatureDateTime,
            doc.SignedByStaffSID,
            doc.CosignedByStaffSID,
            def.TIUDocumentDefinitionPrintName AS NoteTitle,
            txt.ReportText AS NoteText
        FROM {CDWWorkQueryBuilder.NOTE_METADATA_TABLE} doc
        INNER JOIN {CDWWorkQueryBuilder.NOTE_TEXT_TABLE} txt
            ON doc.TIUDocumentSID = txt.TIUDocumentSID
        INNER JOIN {CDWWorkQueryBuilder.NOTE_DEFINITION_TABLE} def
            ON doc.TIUDocumentDefinitionSID = def.TIUDocumentDefinitionSID
        WHERE doc.PatientSID = {patient_sid}
            AND txt.ReportText IS NOT NULL
        """
        
        if start_date:
            query += f"\n            AND doc.ReferenceDateTime >= '{start_date.strftime('%Y-%m-%d')}'"
        
        if end_date:
            query += f"\n            AND doc.ReferenceDateTime <= '{end_date.strftime('%Y-%m-%d')}'"
        
        if note_title_filter:
            conditions = " OR ".join([
                f"def.TIUDocumentDefinitionPrintName LIKE '%{title}%'"
                for title in note_title_filter
            ])
            query += f"\n            AND ({conditions})"
        
        query += "\n        ORDER BY doc.ReferenceDateTime DESC"
        
        return query
    
    @staticmethod
    def get_admission_notes(
        inpatient_sid: int,
        limit: int = 50
    ) -> str:
        """
        Get notes related to a specific admission.
        
        Args:
            inpatient_sid: Inpatient admission identifier
            limit: Maximum number of notes to return
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT TOP {limit}
            doc.TIUDocumentSID,
            doc.PatientSID,
            doc.ReferenceDateTime AS NoteDateTime,
            doc.SignatureDateTime,
            doc.SignedByStaffSID,
            doc.CosignedByStaffSID,
            def.TIUDocumentDefinitionPrintName AS NoteTitle,
            LEN(txt.ReportText) AS TextLength
        FROM {CDWWorkQueryBuilder.NOTE_METADATA_TABLE} doc
        INNER JOIN {CDWWorkQueryBuilder.NOTE_TEXT_TABLE} txt
            ON doc.TIUDocumentSID = txt.TIUDocumentSID
        INNER JOIN {CDWWorkQueryBuilder.NOTE_DEFINITION_TABLE} def
            ON doc.TIUDocumentDefinitionSID = def.TIUDocumentDefinitionSID
        WHERE doc.InpatientSID = {inpatient_sid}
            AND txt.ReportText IS NOT NULL
        ORDER BY doc.ReferenceDateTime ASC
        """
        return query
    
    @staticmethod
    def get_admitting_specialty(inpatient_sid: int) -> str:
        """
        Get the admitting specialty for an admission (earliest specialty transfer).
        
        Args:
            inpatient_sid: Inpatient admission identifier
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT TOP 1
            st.InpatientSID,
            st.PatientSID,
            st.SpecialtyTransferDateTime AS AdmitDateTime,
            st.TreatingSpecialtySID,
            ts.TreatingSpecialtyName AS AdmittingSpecialty
        FROM {CDWWorkQueryBuilder.SPECIALTY_TRANSFER_TABLE} st
        INNER JOIN {CDWWorkQueryBuilder.TREATING_SPECIALTY_TABLE} ts
            ON st.TreatingSpecialtySID = ts.TreatingSpecialtySID
        WHERE st.InpatientSID = {inpatient_sid}
            AND st.SpecialtyTransferDateTime IS NOT NULL
            AND st.TreatingSpecialtySID > 0
        ORDER BY st.SpecialtyTransferDateTime ASC
        """
        return query
    
    @staticmethod
    def get_specialty_transfers(inpatient_sid: int) -> str:
        """
        Get all specialty transfers for an admission.
        
        Args:
            inpatient_sid: Inpatient admission identifier
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT 
            st.SpecialtyTransferSID,
            st.InpatientSID,
            st.PatientSID,
            st.SpecialtyTransferDateTime,
            st.TreatingSpecialtySID,
            ts.TreatingSpecialtyName
        FROM {CDWWorkQueryBuilder.SPECIALTY_TRANSFER_TABLE} st
        INNER JOIN {CDWWorkQueryBuilder.TREATING_SPECIALTY_TABLE} ts
            ON st.TreatingSpecialtySID = ts.TreatingSpecialtySID
        WHERE st.InpatientSID = {inpatient_sid}
            AND st.SpecialtyTransferDateTime IS NOT NULL
        ORDER BY st.SpecialtyTransferDateTime ASC
        """
        return query
    
    @staticmethod
    def get_note_titles_by_keyword(keyword: str, limit: int = 50) -> str:
        """
        Search for note titles containing a keyword.
        
        Args:
            keyword: Keyword to search for in note titles
            limit: Maximum number of results
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT TOP {limit}
            TIUDocumentDefinitionSID,
            TIUDocumentDefinitionPrintName
        FROM {CDWWorkQueryBuilder.NOTE_DEFINITION_TABLE}
        WHERE TIUDocumentDefinitionPrintName LIKE '%{keyword}%'
        ORDER BY TIUDocumentDefinitionPrintName
        """
        return query
    
    @staticmethod
    def get_admissions_by_station(
        station: int,
        start_date: datetime,
        end_date: datetime,
        limit: int = 100
    ) -> str:
        """
        Get admissions for a station within a date range.
        
        Args:
            station: Station number (e.g., 626)
            start_date: Start date for admission range
            end_date: End date for admission range
            limit: Maximum number of admissions
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT TOP {limit}
            InpatientSID,
            PatientSID,
            Sta3n,
            AdmitDateTime,
            DischargeDateTime
        FROM {CDWWorkQueryBuilder.INPATIENT_TABLE}
        WHERE Sta3n = {station}
            AND AdmitDateTime >= '{start_date.strftime('%Y-%m-%d')}'
            AND AdmitDateTime <= '{end_date.strftime('%Y-%m-%d')}'
            AND DischargeDateTime IS NOT NULL
        ORDER BY AdmitDateTime DESC
        """
        return query
    
    @staticmethod
    def get_note_with_full_text(tiu_document_sid: int) -> str:
        """
        Get a single note with full text.
        
        Args:
            tiu_document_sid: TIU document identifier
        
        Returns:
            SQL query string
        """
        query = f"""
        SELECT TOP 1
            doc.TIUDocumentSID,
            doc.PatientSID,
            doc.ReferenceDateTime AS NoteDateTime,
            doc.SignatureDateTime,
            doc.CosignatureDateTime,
            doc.SignedByStaffSID,
            doc.CosignedByStaffSID,
            def.TIUDocumentDefinitionPrintName AS NoteTitle,
            txt.ReportText AS NoteText
        FROM {CDWWorkQueryBuilder.NOTE_METADATA_TABLE} doc
        INNER JOIN {CDWWorkQueryBuilder.NOTE_TEXT_TABLE} txt
            ON doc.TIUDocumentSID = txt.TIUDocumentSID
        INNER JOIN {CDWWorkQueryBuilder.NOTE_DEFINITION_TABLE} def
            ON doc.TIUDocumentDefinitionSID = def.TIUDocumentDefinitionSID
        WHERE doc.TIUDocumentSID = {tiu_document_sid}
        """
        return query
