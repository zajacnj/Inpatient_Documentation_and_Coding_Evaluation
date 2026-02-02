"""
VA GPT Client for Document Analysis
Integrates with VA GPT (Azure OpenAI) for clinical document analysis and diagnosis extraction.
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

# Load environment variables from Key.env
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / 'Key.env'
    if env_file.exists():
        load_dotenv(env_file)
except ImportError:
    pass

# Try to import OpenAI/VA GPT
try:
    from openai import AzureOpenAI, OpenAI
except ImportError:
    print("Warning: OpenAI library not found. Install with: pip install openai")
    AzureOpenAI = None
    OpenAI = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VAGPTClient:
    """Client for VA GPT document analysis and diagnosis extraction."""

    def __init__(self, api_key: str = None, use_azure: bool = True):
        """
        Initialize VA GPT client.

        Args:
            api_key: OpenAI/Azure API key (defaults to Key.env)
            use_azure: Whether to use Azure OpenAI or standard OpenAI
        """
        self.api_key = api_key
        self.use_azure = use_azure
        self.client = None
        self.conversation_history = []

        # Initialize API client
        self._init_api_client()

    def _init_api_client(self):
        """Initialize OpenAI/Azure OpenAI client using VA GPT configuration."""
        if not AzureOpenAI and not OpenAI:
            logger.warning("OpenAI library not installed")
            return

        # Get API key from environment
        api_key = self.api_key or os.getenv('VA_AI_API_KEY')

        if not api_key:
            logger.warning("No API key found. Set VA_AI_API_KEY in Key.env file")
            return

        try:
            if self.use_azure:
                # VA GPT Azure OpenAI configuration
                logger.info("Initializing Azure OpenAI with VA GPT endpoint...")
                self.client = AzureOpenAI(
                    api_key=api_key,
                    api_version="2024-02-15-preview",
                    azure_endpoint="https://spd-prod-openai-va-apim.azure-api.us/api"
                )
                logger.info("Initialized VA GPT (Azure OpenAI) client")
            else:
                # Fallback to standard OpenAI
                logger.info("Initializing standard OpenAI client...")
                self.client = OpenAI(api_key=api_key)
                logger.info("Initialized OpenAI client")

        except Exception as e:
            logger.error(f"Error initializing API client: {type(e).__name__}: {str(e)}", exc_info=True)
            self.client = None

    def analyze_clinical_note(
        self,
        note_text: str,
        note_type: str,
        patient_context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Analyze a clinical note to extract diagnoses and clinical findings.

        Args:
            note_text: The text content of the clinical note
            note_type: Type of note (Admission, Progress, Consult, etc.)
            patient_context: Optional context about the patient (vitals, labs, etc.)

        Returns:
            Dict with extracted diagnoses, findings, and confidence scores
        """
        if not self.client:
            return {
                'success': False,
                'error': 'API client not initialized. Check API credentials.',
                'diagnoses': []
            }

        # Build context from patient data if available
        context_section = ""
        if patient_context:
            if patient_context.get('vitals'):
                context_section += "\n\nRECENT VITAL SIGNS:\n"
                for vital in patient_context['vitals'][:10]:
                    context_section += f"- {vital.get('type', 'Unknown')}: {vital.get('value', 'N/A')} ({vital.get('datetime', 'N/A')})\n"

            if patient_context.get('labs'):
                context_section += "\n\nRECENT LABORATORY VALUES:\n"
                for lab in patient_context['labs'][:20]:
                    context_section += f"- {lab.get('test', 'Unknown')}: {lab.get('value', 'N/A')} {lab.get('units', '')} ({lab.get('datetime', 'N/A')})\n"

        system_prompt = f"""You are an expert clinical documentation analyst and medical coder.
Your task is to analyze clinical notes and extract diagnoses that are documented or strongly supported by clinical evidence.

INSTRUCTIONS:
1. Identify all diagnoses that are explicitly documented in the note
2. Identify diagnoses that are strongly implied by documented findings, vital signs, and lab values
3. For each diagnosis, provide:
   - The diagnosis name
   - The ICD-10-CM code (if you can determine it)
   - Whether it's the principal diagnosis or a secondary/comorbidity
   - Supporting evidence from the note
   - Confidence level (HIGH, MEDIUM, LOW)
4. Distinguish between:
   - DOCUMENTED: Explicitly stated in the note
   - INFERRED: Strongly supported by clinical evidence but not explicitly stated
5. Consider the diagnostic criteria for each condition

IMPORTANT:
- Be conservative - only include diagnoses with clear clinical support
- Use standard ICD-10-CM codes
- Note if a diagnosis might be under-coded (e.g., unspecified when specificity is documented)

NOTE TYPE: {note_type}
{context_section}

Respond in JSON format:
{{
    "principal_diagnosis": {{
        "name": "...",
        "icd10_code": "...",
        "type": "DOCUMENTED" or "INFERRED",
        "evidence": ["..."],
        "confidence": "HIGH/MEDIUM/LOW"
    }},
    "secondary_diagnoses": [
        {{
            "name": "...",
            "icd10_code": "...",
            "type": "DOCUMENTED" or "INFERRED",
            "evidence": ["..."],
            "confidence": "HIGH/MEDIUM/LOW"
        }}
    ],
    "potential_undercoding": [
        {{
            "current": "...",
            "suggested": "...",
            "reason": "..."
        }}
    ],
    "clinical_summary": "Brief summary of key clinical findings"
}}"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this clinical note:\n\n{note_text}"}
                ],
                temperature=0.2,
                max_tokens=4000
            )

            response_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                # Find JSON in response
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response_text[json_start:json_end])
                    return {
                        'success': True,
                        'analysis': result,
                        'raw_response': response_text
                    }
            except json.JSONDecodeError:
                pass

            # Return raw response if JSON parsing fails
            return {
                'success': True,
                'analysis': None,
                'raw_response': response_text
            }

        except Exception as e:
            logger.error(f"Error analyzing clinical note: {e}")
            return {
                'success': False,
                'error': str(e),
                'diagnoses': []
            }

    def summarize_note(self, note_text: str, max_length: int = 500) -> Dict[str, Any]:
        """
        Summarize a clinical note to reduce token usage for multi-note analysis.

        Args:
            note_text: The text content of the clinical note
            max_length: Target maximum length for summary

        Returns:
            Dict with summary and key findings
        """
        if not self.client:
            return {
                'success': False,
                'error': 'API client not initialized.',
                'summary': None
            }

        system_prompt = """You are a clinical documentation specialist.
Summarize the following clinical note, preserving:
1. All diagnoses mentioned (explicitly or implied)
2. Key vital signs and lab abnormalities
3. Significant procedures or treatments
4. Important clinical findings

Keep the summary concise but complete for coding purposes.
Format: A single paragraph followed by a bulleted list of diagnoses."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Summarize this note (target {max_length} characters):\n\n{note_text}"}
                ],
                temperature=0.2,
                max_tokens=1000
            )

            return {
                'success': True,
                'summary': response.choices[0].message.content
            }

        except Exception as e:
            logger.error(f"Error summarizing note: {e}")
            return {
                'success': False,
                'error': str(e),
                'summary': None
            }

    def compare_diagnoses(
        self,
        documented_diagnoses: List[Dict],
        coded_diagnoses: List[Dict]
    ) -> Dict[str, Any]:
        """
        Compare AI-extracted diagnoses against actually coded diagnoses.

        Args:
            documented_diagnoses: Diagnoses extracted from clinical notes
            coded_diagnoses: Actual ICD-10 codes from PTF

        Returns:
            Dict with comparison analysis
        """
        if not self.client:
            return {
                'success': False,
                'error': 'API client not initialized.',
                'comparison': None
            }

        system_prompt = """You are an expert medical coder and clinical documentation improvement specialist.
Compare the diagnoses extracted from clinical documentation against the actually coded diagnoses.

Identify:
1. MATCHES: Diagnoses that are both documented and coded
2. DOCUMENTED BUT NOT CODED: Diagnoses supported by documentation but not in the coded list
3. CODED BUT NOT CLEARLY DOCUMENTED: Codes that lack clear documentation support
4. SPECIFICITY OPPORTUNITIES: Where more specific codes could be used based on documentation
5. POTENTIAL DRG IMPACT: How discrepancies might affect DRG assignment

Respond in JSON format:
{{
    "matches": [
        {{"documented": "...", "coded": "...", "icd10": "..."}}
    ],
    "documented_not_coded": [
        {{"diagnosis": "...", "suggested_icd10": "...", "evidence": "...", "impact": "..."}}
    ],
    "coded_not_documented": [
        {{"icd10": "...", "description": "...", "concern": "..."}}
    ],
    "specificity_opportunities": [
        {{"current_code": "...", "suggested_code": "...", "reason": "..."}}
    ],
    "summary": "Overall assessment of documentation and coding alignment",
    "recommendations": ["..."]
}}"""

        try:
            user_content = f"""DOCUMENTED DIAGNOSES (from clinical notes):
{json.dumps(documented_diagnoses, indent=2)}

CODED DIAGNOSES (from PTF/billing):
{json.dumps(coded_diagnoses, indent=2)}

Please compare and analyze."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.2,
                max_tokens=4000
            )

            response_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response_text[json_start:json_end])
                    return {
                        'success': True,
                        'comparison': result,
                        'raw_response': response_text
                    }
            except json.JSONDecodeError:
                pass

            return {
                'success': True,
                'comparison': None,
                'raw_response': response_text
            }

        except Exception as e:
            logger.error(f"Error comparing diagnoses: {e}")
            return {
                'success': False,
                'error': str(e),
                'comparison': None
            }

    def consolidate_analyses(
        self,
        note_analyses: List[Dict],
        patient_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Consolidate multiple note analyses into a final diagnosis list.

        Args:
            note_analyses: List of individual note analysis results
            patient_info: Optional patient demographic/admission info

        Returns:
            Dict with consolidated diagnosis list
        """
        if not self.client:
            return {
                'success': False,
                'error': 'API client not initialized.',
                'consolidated': None
            }

        system_prompt = """You are a clinical documentation improvement specialist.
You are given multiple analyses of clinical notes from a single hospital admission.
Consolidate these into a single, comprehensive list of diagnoses.

INSTRUCTIONS:
1. Identify the most likely PRINCIPAL DIAGNOSIS based on:
   - What primarily led to the admission
   - Which diagnosis consumed the most resources
   - Documentation from attending physicians
2. List all SECONDARY DIAGNOSES/COMORBIDITIES that:
   - Were present on admission (POA) or developed during stay
   - Affected patient care or length of stay
3. For each diagnosis, determine:
   - Best ICD-10-CM code based on documented specificity
   - Level of confidence (based on documentation support)
   - Whether it's POA (Present on Admission) or developed during hospitalization

Respond in JSON format:
{{
    "principal_diagnosis": {{
        "name": "...",
        "icd10_code": "...",
        "confidence": "HIGH/MEDIUM/LOW",
        "poa": true/false,
        "supporting_notes": ["note types that support this"]
    }},
    "secondary_diagnoses": [
        {{
            "name": "...",
            "icd10_code": "...",
            "confidence": "HIGH/MEDIUM/LOW",
            "poa": true/false,
            "cc_mcc": "CC" or "MCC" or "None",
            "supporting_notes": ["..."]
        }}
    ],
    "clinical_summary": "Brief narrative of hospitalization",
    "documentation_quality": "Assessment of overall documentation quality",
    "recommendations": ["Specific CDI recommendations"]
}}"""

        try:
            # Build context from note analyses
            analyses_text = ""
            for i, analysis in enumerate(note_analyses, 1):
                analyses_text += f"\n--- NOTE ANALYSIS {i} ---\n"
                analyses_text += json.dumps(analysis, indent=2)
                analyses_text += "\n"

            patient_context = ""
            if patient_info:
                patient_context = f"\n\nPATIENT CONTEXT:\n{json.dumps(patient_info, indent=2)}"

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Consolidate these note analyses:{patient_context}\n{analyses_text}"}
                ],
                temperature=0.2,
                max_tokens=4000
            )

            response_text = response.choices[0].message.content

            # Try to parse JSON response
            try:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    result = json.loads(response_text[json_start:json_end])
                    return {
                        'success': True,
                        'consolidated': result,
                        'raw_response': response_text
                    }
            except json.JSONDecodeError:
                pass

            return {
                'success': True,
                'consolidated': None,
                'raw_response': response_text
            }

        except Exception as e:
            logger.error(f"Error consolidating analyses: {e}")
            return {
                'success': False,
                'error': str(e),
                'consolidated': None
            }

    def is_initialized(self) -> bool:
        """Check if the client is properly initialized."""
        return self.client is not None
