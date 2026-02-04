#!/usr/bin/env python3
"""
Specialty code mapping based on VA standards and VSSC data definitions.
Maps database specialty codes to clinical display names.
"""

# Create a mapping dictionary for specialty codes to display names
SPECIALTY_CODE_MAP = {
    # Based on DischargeFromService codes + LOSInService
    # and D02_VISN09 specialty descriptions
    ('M', 0): 'OBSERVATION',           # Medicine with 0 LOS = Observation
    ('M', None): 'MEDICAL',            # Medicine (general)
    ('S', None): 'SURGICAL',           # Surgery
    ('P', None): 'PSYCHIATRIC',        # Psychiatry
    ('R', None): 'REHABILITATION',     # Rehabilitation
    ('NH', None): 'HOSPICE/LONG-TERM CARE',  # Nursing Home / Long-term care
    
    # D02_VISN09 SpecialtyDesc mappings - Medical Specialties
    'GENERAL(ACUTE MEDICINE)': 'MEDICAL OBSERVATION',
    'GEN MEDICINE (ACUTE)': 'MEDICAL',
    'INTERMEDIATE MEDICINE': 'MEDICAL',
    'MEDICAL ICU': 'MEDICAL',
    'MEDICAL STEP DOWN': 'MEDICAL',
    'MEDICAL OBSERVATION': 'MEDICAL OBSERVATION',
    'TELEMETRY': 'MEDICAL',
    'GEM ACUTE MEDICINE': 'MEDICAL',
    'RESPITE CARE (MEDICINE)': 'MEDICAL',
    'zGENERAL(ACUTE MEDICINE': 'MEDICAL',
    'REHAB MEDICINE OBSERVATION': 'REHABILITATION',
    'REHABILITATION MEDICINE': 'REHABILITATION',
    
    # Medical Subspecialties
    'CARDIOLOGY': 'MEDICAL',
    'NEUROLOGY': 'MEDICAL',
    'zzneurology': 'MEDICAL',
    'HEMATOLOGY/ONCOLOGY': 'MEDICAL',
    'PULMONARY, NON-TB': 'MEDICAL',
    'METABOLIC': 'MEDICAL',
    'GERONTOLOGY': 'MEDICAL',
    'GASTROENTEROLOGY': 'MEDICAL',
    'DERMATOLOGY': 'MEDICAL',
    'EPILEPSY CENTER': 'MEDICAL',
    
    # Cardiac Units
    'CARDIAC-STEP DOWN UNIT': 'MEDICAL',
    'CARDIAC INTENSIVE CARE UNIT': 'MEDICAL',
    
    # Surgical Specialties
    'GENERAL SURGERY': 'SURGICAL',
    'THORACIC SURGERY': 'SURGICAL',
    'NEUROSURGERY': 'SURGICAL',
    'CARDIAC SURGERY': 'SURGICAL',
    'PLASTIC SURGERY': 'SURGICAL',
    'ORAL SURGERY': 'SURGICAL',
    'ORTHOPEDIC': 'SURGICAL',
    'UROLOGY': 'SURGICAL',
    'VASCULAR': 'SURGICAL',
    'PERIPHERAL VASCULAR': 'SURGICAL',
    'EAR, NOSE, THROAT (ENT)': 'SURGICAL',
    'ANESTHESIOLOGY': 'SURGICAL',
    'TRANSPLANTATION': 'SURGICAL',
    'OB/GYN': 'SURGICAL',
    'PODIATRY': 'SURGICAL',
    'OPHTHALMOLOGY': 'SURGICAL',
    'SURGICAL ICU': 'SURGICAL',
    'SURGICAL STEPDOWN': 'SURGICAL',
    'SURGICAL OBSERVATION': 'SURGICAL',
    
    # Psychiatric Services
    'HIGH INTENSITY GEN PSYCH INPAT': 'PSYCHIATRIC',
    'GEN INTERMEDIATE PSYCH': 'PSYCHIATRIC',
    'PSYCH RESID REHAB TRMT PROG': 'PSYCHIATRIC',
    'ACUTE PSYCHIATRY (<45 DAYS)': 'PSYCHIATRIC',
    'PSYCH RESID REHAB PROG': 'PSYCHIATRIC',
    'GEM PSYCHIATRIC BEDS': 'PSYCHIATRIC',
    'PSYCHIATRY': 'PSYCHIATRIC',
    'PSYCHIATRIC OBSERVATION': 'PSYCHIATRIC',
    
    # PTSD Programs
    'PTSD RESIDENTIAL REHAB PROG': 'PSYCHIATRIC',
    'SIPU (SPEC INPT PTSD UNIT)': 'PSYCHIATRIC',
    'PTSD RESID REHAB PROG': 'PSYCHIATRIC',
    'EVAL/BRF TRMT PTSD UNIT(EBTPU)': 'PSYCHIATRIC',
    'PTSD CWT/TR': 'PSYCHIATRIC',
    'DOMICILIARY PTSD': 'PSYCHIATRIC',
    
    # Substance Abuse Programs
    'SUBSTANCE ABUSE TRMT UNIT': 'PSYCHIATRIC',
    'SUBSTANCE ABUSE RES TRMT PROG': 'PSYCHIATRIC',
    'SUBSTANCE ABUSE RESID PROG': 'PSYCHIATRIC',
    'SUBSTANCE ABUSE INTERMED CARE': 'PSYCHIATRIC',
    'DRUG DEPENDENCE TRMT UNIT': 'PSYCHIATRIC',
    'ALCOHOL DEPENDENCE TRMT UNIT': 'PSYCHIATRIC',
    'DOMICILIARY SUBSTANCE ABUSE': 'PSYCHIATRIC',
    'DOMICILIARY SUBSTANCE USE DO': 'PSYCHIATRIC',
    'SUBST ABUSE CWT/TRANS RESID': 'PSYCHIATRIC',
    
    # Rehabilitation Services
    'BLIND REHAB': 'REHABILITATION',
    'BLIND REHAB OBSERVATION': 'REHABILITATION',
    'SPINAL CORD INJURY': 'REHABILITATION',
    'SPINAL CORD INJURY OBSERVATION': 'REHABILITATION',
    'SPINAL CORD INJURY LTC CENTER': 'REHABILITATION',
    'PM&R TRANSITIONAL REHAB': 'REHABILITATION',
    'POLYTRAUMA REHAB UNIT': 'REHABILITATION',
    
    # Nursing Home / Long-term Care
    'NHCU': 'HOSPICE/LONG-TERM CARE',
    'NH HOSPICE': 'HOSPICE/LONG-TERM CARE',
    'NH GEM NURSING HOME CARE': 'HOSPICE/LONG-TERM CARE',
    'NH SHORT STAY SKILLED NURSING': 'HOSPICE/LONG-TERM CARE',
    'NH LONG STAY DEMENTIA CARE': 'HOSPICE/LONG-TERM CARE',
    'NH LONG-STAY CONTINUING CARE': 'HOSPICE/LONG-TERM CARE',
    'NH SHORT STAY REHABILITATION': 'HOSPICE/LONG-TERM CARE',
    'NH SHORT-STAY CONTINUING CARE': 'HOSPICE/LONG-TERM CARE',
    'NH SHORT STAY DEMENTIA CARE': 'HOSPICE/LONG-TERM CARE',
    'NH LONG-STAY MH RECOVERY': 'HOSPICE/LONG-TERM CARE',
    'NH SHORT-STAY MH RECOVERY': 'HOSPICE/LONG-TERM CARE',
    'NH LONG STAY SPINAL CORD INJ': 'HOSPICE/LONG-TERM CARE',
    'NH LONG STAY SKILLED NURSING': 'HOSPICE/LONG-TERM CARE',
    'NH RESPITE CARE (NHCU)': 'HOSPICE/LONG-TERM CARE',
    'HOSPICE FOR ACUTE CARE': 'HOSPICE/LONG-TERM CARE',
    
    # Domiciliary Services (Residential)
    'DOMICILIARY': 'RESIDENTIAL',
    'DOMICILIARY CHV': 'RESIDENTIAL',
    'DOMICILIARY GENERAL': 'RESIDENTIAL',
    'GENERAL CWT/TR': 'RESIDENTIAL',
    'HOMELESS CWT/TRANS RESID': 'RESIDENTIAL',
    'STAR I, II & III': 'RESIDENTIAL',
    
    # Observation/Stepdown
    'GEM INTERMEDIATE CARE': 'MEDICAL',
    'NEUROLOGY OBSERVATION': 'MEDICAL',
    'ED OBSERVATION': 'MEDICAL OBSERVATION',
    
    # Other
    'NON-DOD BEDS IN VA FACILITY': 'MEDICAL',
    '*Unknown at this time*': 'UNKNOWN',
}

def map_specialty_display(specialty_desc, discharge_service=None, los_in_service=None):
    """
    Map database specialty description to user-facing display name.
    
    Args:
        specialty_desc: Specialty description from database (e.g., 'GENERAL(ACUTE MEDICINE)')
        discharge_service: DischargeFromService code (e.g., 'M', 'NH', 'S')
        los_in_service: Length of service integer value
        
    Returns:
        User-friendly specialty name for display
    """
    # Try exact mapping first
    if specialty_desc in SPECIALTY_CODE_MAP:
        return SPECIALTY_CODE_MAP[specialty_desc]
    
    # Try partial matches
    if specialty_desc:
        desc_lower = specialty_desc.upper()
        if 'MEDICINE' in desc_lower and 'ACUTE' in desc_lower and los_in_service == 0:
            return 'OBSERVATION'
        if 'MEDICINE' in desc_lower:
            return 'MEDICAL'
        if 'NHCU' in desc_lower or 'NURSING' in desc_lower or 'LONG STAY' in desc_lower:
            return 'HOSPICE/LONG-TERM CARE'
        if 'SURGERY' in desc_lower:
            return 'SURGICAL'
        if 'PSYCH' in desc_lower:
            return 'PSYCHIATRIC'
    
    # Try service code if specialty description doesn't match
    if discharge_service and (discharge_service, los_in_service) in SPECIALTY_CODE_MAP:
        return SPECIALTY_CODE_MAP[(discharge_service, los_in_service)]
    
    # Default fallback
    return specialty_desc if specialty_desc else 'UNKNOWN'


# Test the mapping
if __name__ == "__main__":
    test_cases = [
        ('GENERAL(ACUTE MEDICINE)', None, 0),
        ('GENERAL(ACUTE MEDICINE)', 'M', 0),
        ('NHCU', None, None),
        ('NHCU', 'NH', 11),
    ]
    
    for spec_desc, svc, los in test_cases:
        result = map_specialty_display(spec_desc, svc, los)
        print(f"({spec_desc}, {svc}, {los}) -> {result}")
