"""Prompt templates for compliance analysis against various frameworks.

This module provides structured prompts for analyzing vendor documents
against compliance frameworks like SOC 2, ISO 27001, NIST CSF, and CIS Controls.
"""

from typing import Any

# System prompt for compliance analysis
COMPLIANCE_ANALYSIS_SYSTEM_PROMPT = """You are an expert compliance analyst specializing in vendor security assessments and third-party risk management. You have deep expertise in:

- SOC 2 Trust Service Criteria (Security, Availability, Processing Integrity, Confidentiality, Privacy)
- ISO 27001 Information Security Management Systems
- NIST Cybersecurity Framework (Identify, Protect, Detect, Respond, Recover)
- CIS Critical Security Controls v8
- HIPAA Security Rule
- PCI DSS v4.0

Your task is to analyze vendor security documentation and identify compliance gaps, concerns, or areas requiring follow-up. You must:

1. **Be Evidence-Based**: Every finding must cite specific text from the document
2. **Be Specific**: Reference exact control IDs and requirements from the framework
3. **Assess Severity Accurately**: Use the severity criteria provided
4. **Provide Actionable Remediation**: Give concrete steps to address each finding
5. **Include Page References**: Always note the page number where evidence was found

Severity Levels:
- **CRITICAL**: Fundamental control missing or complete failure; immediate business risk; regulatory violation likely
- **HIGH**: Significant control gap; material weakness; requires urgent remediation within 30 days
- **MEDIUM**: Partial control implementation; improvement needed; remediate within 90 days
- **LOW**: Minor gap or documentation issue; best practice improvement; remediate within 180 days
- **INFO**: Observation or recommendation; no immediate action required; consider for future improvement

Always respond in valid JSON format as specified in the user prompt."""


# Framework-specific analysis context
FRAMEWORK_CONTEXTS: dict[str, dict[str, str]] = {
    "soc2": {
        "name": "SOC 2 Type II",
        "focus_areas": """
Focus your analysis on the Trust Service Criteria:
- CC (Common Criteria/Security): Control environment, risk assessment, information/communication, monitoring
- A (Availability): System availability commitments and performance
- PI (Processing Integrity): System processing completeness and accuracy
- C (Confidentiality): Protection of confidential information
- P (Privacy): Personal information collection, use, retention, disclosure""",
        "key_questions": """
Key questions to address:
1. Are there clear descriptions of controls and their operating effectiveness?
2. Is there evidence of management's assertion and auditor's opinion?
3. Are there any qualified opinions, exceptions, or deviations noted?
4. Is the scope clearly defined and appropriate for the services provided?
5. Are complementary user entity controls (CUECs) clearly documented?
6. What is the testing period and are there any gaps in coverage?""",
    },
    "iso27001": {
        "name": "ISO 27001",
        "focus_areas": """
Focus your analysis on the ISMS requirements:
- Context of the organization and scope definition
- Leadership commitment and information security policy
- Risk assessment and treatment methodology
- Statement of Applicability (SoA) completeness
- Annex A controls implementation (A.5-A.18)
- Internal audit and management review processes
- Continual improvement mechanisms""",
        "key_questions": """
Key questions to address:
1. Is the ISMS scope clearly defined and appropriate?
2. Is there evidence of risk assessment methodology and results?
3. Are controls from Annex A properly addressed in the SoA?
4. Is there evidence of internal audits and their findings?
5. Are nonconformities tracked and addressed?
6. Is the certification current and from an accredited body?""",
    },
    "nist_csf": {
        "name": "NIST Cybersecurity Framework",
        "focus_areas": """
Focus your analysis on the five core functions:
- IDENTIFY (ID): Asset management, risk assessment, governance
- PROTECT (PR): Access control, awareness training, data security
- DETECT (DE): Anomalies and events, continuous monitoring
- RESPOND (RS): Response planning, communications, analysis
- RECOVER (RC): Recovery planning, improvements, communications""",
        "key_questions": """
Key questions to address:
1. Is there comprehensive asset inventory and classification?
2. Are access controls documented and regularly reviewed?
3. Is there evidence of security awareness training?
4. Are monitoring and detection capabilities described?
5. Is there an incident response plan and evidence of testing?
6. Are business continuity and disaster recovery plans documented?""",
    },
    "cis_controls": {
        "name": "CIS Critical Security Controls v8",
        "focus_areas": """
Focus your analysis on the control categories:
- Basic Controls (1-6): Inventory, data protection, secure configuration, access control, account management, vulnerability management
- Foundational Controls (7-12): Email/browser protection, malware defense, data recovery, network monitoring, network device configuration, boundary defense
- Organizational Controls (13-18): Security awareness, application security, incident response, penetration testing, service provider management""",
        "key_questions": """
Key questions to address:
1. Is there evidence of asset inventory (hardware and software)?
2. Are secure configurations documented and enforced?
3. Is vulnerability management process defined?
4. Are access controls based on least privilege?
5. Is there evidence of security awareness training?
6. Are incident response procedures documented and tested?""",
    },
    "hipaa": {
        "name": "HIPAA Security Rule",
        "focus_areas": """
Focus your analysis on the HIPAA safeguards:
- Administrative Safeguards: Security management, workforce security, information access, training
- Physical Safeguards: Facility access, workstation security, device controls
- Technical Safeguards: Access control, audit controls, integrity, transmission security
- Organizational Requirements: BAA provisions, policies and procedures""",
        "key_questions": """
Key questions to address:
1. Is there evidence of risk analysis and risk management?
2. Are workforce security measures documented?
3. Is PHI access appropriately controlled and audited?
4. Are encryption requirements addressed?
5. Are business associate agreements in place?
6. Is there evidence of security awareness training?""",
    },
    "pci_dss": {
        "name": "PCI DSS v4.0",
        "focus_areas": """
Focus your analysis on the PCI DSS requirements:
- Requirement 1-2: Network security and secure configurations
- Requirement 3-4: Account data protection and encryption
- Requirement 5-6: Malware protection and secure development
- Requirement 7-9: Access control and physical security
- Requirement 10-11: Logging, monitoring, and testing
- Requirement 12: Security policies and procedures""",
        "key_questions": """
Key questions to address:
1. Is the cardholder data environment (CDE) clearly defined?
2. Is cardholder data properly protected (encryption, masking)?
3. Are access controls implemented on least privilege basis?
4. Is there evidence of regular vulnerability scanning and penetration testing?
5. Are security policies and procedures documented?
6. Is there evidence of security awareness training?""",
    },
}


def get_framework_context(framework_id: str) -> dict[str, str]:
    """Get the analysis context for a specific framework.

    Args:
        framework_id: The framework identifier (e.g., 'soc2', 'iso27001')

    Returns:
        Dictionary with framework name, focus areas, and key questions
    """
    # Normalize framework ID
    normalized_id = framework_id.lower().replace("-", "_").replace(" ", "_")

    # Handle common variations
    id_mapping = {
        "nist_800_53": "nist_csf",
        "iso_27001": "iso27001",
    }
    normalized_id = id_mapping.get(normalized_id, normalized_id)

    return FRAMEWORK_CONTEXTS.get(
        normalized_id,
        {
            "name": framework_id,
            "focus_areas": "Analyze against general security best practices and the specified framework requirements.",
            "key_questions": "Look for gaps in security controls, missing documentation, and areas of concern.",
        },
    )


def build_compliance_analysis_prompt(
    document_context: str,
    framework_id: str,
    document_type: str,
    controls: list[dict[str, Any]] | None = None,
    custom_focus_areas: list[str] | None = None,
) -> str:
    """Build a comprehensive compliance analysis prompt.

    Args:
        document_context: Formatted document content with chunk references
        framework_id: The compliance framework to analyze against
        document_type: Type of document (e.g., 'soc2_report', 'security_policy')
        controls: Optional list of specific framework controls to check
        custom_focus_areas: Optional list of specific areas to focus on

    Returns:
        Formatted prompt string for LLM analysis
    """
    framework_ctx = get_framework_context(framework_id)

    # Build controls section if provided
    controls_section = ""
    if controls:
        controls_text = []
        for control in controls[:20]:  # Limit to 20 controls to avoid token limits
            ctrl_id = control.get("id", "")
            ctrl_name = control.get("name", "")
            ctrl_desc = control.get("description", "")
            controls_text.append(f"- **{ctrl_id}** ({ctrl_name}): {ctrl_desc}")
        controls_section = f"""
## Specific Controls to Evaluate

{chr(10).join(controls_text)}
"""

    # Build custom focus areas if provided
    focus_section = framework_ctx["focus_areas"]
    if custom_focus_areas:
        custom_focus = "\n".join(f"- {area}" for area in custom_focus_areas)
        focus_section = f"""
{framework_ctx["focus_areas"]}

### Additional Focus Areas Requested:
{custom_focus}
"""

    prompt = f"""## Compliance Analysis Request

**Framework**: {framework_ctx["name"]}
**Document Type**: {document_type.upper().replace("_", " ")}

### Analysis Focus
{focus_section}

### Key Questions
{framework_ctx["key_questions"]}
{controls_section}
### Document Content

The following excerpts are from the vendor's documentation. Each excerpt includes:
- An excerpt number for reference
- Section header (if available)
- Page number (if available)

{document_context}

---

## Required Output

Analyze the document excerpts and provide your findings in the following JSON format:

```json
{{
    "findings": [
        {{
            "title": "Clear, specific finding title",
            "severity": "critical|high|medium|low|info",
            "framework_control": "Specific control ID (e.g., CC6.1, A.9.2.3)",
            "description": "Detailed description of the gap or concern identified",
            "evidence": {{
                "excerpt_number": 1,
                "page_number": 5,
                "quoted_text": "Exact quote from document supporting this finding"
            }},
            "impact": "Business impact if this gap is not addressed",
            "remediation": "Specific steps to remediate this finding",
            "confidence": 0.85
        }}
    ],
    "overall_assessment": {{
        "summary": "Brief overall assessment of the document",
        "strengths": ["List of well-addressed areas"],
        "critical_gaps": ["List of most important gaps to address"],
        "recommended_follow_up": ["Suggested follow-up questions or document requests"]
    }},
    "metadata": {{
        "framework": "{framework_id}",
        "document_type": "{document_type}",
        "excerpts_analyzed": <number>,
        "confidence_score": 0.0-1.0
    }}
}}
```

**Important Instructions**:
1. Only report findings where you have specific evidence from the document
2. Always include the exact excerpt number and page number in evidence
3. Quote relevant text directly - do not paraphrase evidence
4. Assign severity based on the criteria in your system prompt
5. Ensure framework_control references valid control IDs for {framework_ctx["name"]}
6. If the document does not address a critical control, note this as a finding
7. Confidence should reflect how certain you are about the finding (0.0-1.0)
"""

    return prompt


def build_chunk_context(
    chunks: list[dict[str, Any]],
    include_metadata: bool = True,
) -> str:
    """Build formatted context from document chunks.

    Args:
        chunks: List of chunk dictionaries with content and metadata
        include_metadata: Whether to include section headers and page numbers

    Returns:
        Formatted string of document context
    """
    context_parts = []

    for i, chunk in enumerate(chunks):
        content = chunk.get("content", "").strip()
        if not content:
            continue

        # Build header line
        header_parts = [f"--- Excerpt {i + 1}"]

        if include_metadata:
            section = chunk.get("section_header")
            page = chunk.get("page_number")
            chunk_id = chunk.get("id")

            if section:
                header_parts.append(f"[Section: {section}]")
            if page:
                header_parts.append(f"[Page: {page}]")
            if chunk_id:
                header_parts.append(f"[ID: {chunk_id}]")

        header_parts.append("---")
        header = " ".join(header_parts)

        context_parts.append(f"{header}\n{content}")

    return "\n\n".join(context_parts)


def build_targeted_analysis_prompt(
    document_context: str,
    framework_id: str,
    specific_controls: list[dict[str, Any]],
    prior_findings: list[dict[str, Any]] | None = None,
) -> str:
    """Build a targeted analysis prompt for specific controls.

    This is useful for deep-dive analysis on particular control areas.

    Args:
        document_context: Formatted document content
        framework_id: The compliance framework
        specific_controls: List of specific controls to analyze
        prior_findings: Optional list of findings from initial analysis to expand on

    Returns:
        Formatted prompt string
    """
    framework_ctx = get_framework_context(framework_id)

    controls_detail = []
    for ctrl in specific_controls:
        ctrl_text = f"""
### Control: {ctrl.get('id', 'Unknown')} - {ctrl.get('name', 'Unnamed')}

**Description**: {ctrl.get('description', 'No description')}

**Requirements**:
"""
        requirements = ctrl.get("requirements", [])
        for req in requirements:
            ctrl_text += f"- {req.get('id', '')}: {req.get('description', '')}\n"
            if req.get("guidance"):
                ctrl_text += f"  - Guidance: {req.get('guidance')}\n"

        controls_detail.append(ctrl_text)

    prior_findings_section = ""
    if prior_findings:
        prior_text = []
        for finding in prior_findings:
            prior_text.append(
                f"- {finding.get('title', 'Unknown')}: {finding.get('description', '')}"
            )
        prior_findings_section = f"""
## Prior Findings to Expand Upon

The following findings were identified in initial analysis. Please provide deeper analysis:

{chr(10).join(prior_text)}
"""

    return f"""## Targeted Control Analysis

**Framework**: {framework_ctx["name"]}

You are performing a detailed analysis of specific controls against the provided documentation.

## Controls to Analyze
{chr(10).join(controls_detail)}
{prior_findings_section}
## Document Content

{document_context}

---

## Required Output

Provide detailed analysis for each control in JSON format:

```json
{{
    "control_assessments": [
        {{
            "control_id": "Control ID",
            "control_name": "Control name",
            "assessment_status": "fully_addressed|partially_addressed|not_addressed|insufficient_evidence",
            "findings": [
                {{
                    "title": "Finding title",
                    "severity": "critical|high|medium|low|info",
                    "description": "Detailed description",
                    "evidence": {{
                        "excerpt_number": 1,
                        "page_number": 5,
                        "quoted_text": "Exact quote"
                    }},
                    "gap_analysis": "What is missing or insufficient",
                    "remediation": "Recommended actions",
                    "confidence": 0.85
                }}
            ],
            "requirements_coverage": [
                {{
                    "requirement_id": "Requirement ID",
                    "status": "met|partially_met|not_met|not_applicable",
                    "notes": "Brief assessment notes"
                }}
            ]
        }}
    ],
    "summary": {{
        "controls_fully_addressed": 0,
        "controls_partially_addressed": 0,
        "controls_not_addressed": 0,
        "overall_confidence": 0.0-1.0
    }}
}}
```
"""
