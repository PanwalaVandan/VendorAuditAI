"""Analysis service for document compliance analysis.

This module provides enhanced RAG-based compliance analysis that:
- Uses structured compliance framework data
- Generates findings with proper severity levels
- Includes page-specific citations from document chunks
- Links findings to the correct framework controls
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import DocumentChunk
from app.models.document import Document
from app.models.finding import AnalysisRun, Finding, FindingSeverity
from app.prompts.compliance_analysis import (
    build_chunk_context,
    build_compliance_analysis_prompt,
)
from app.services.compliance import (
    get_framework_controls,
    get_framework_summary,
)
from app.models.custom_framework import CustomFramework
from app.services.llm import SUPPORTED_FRAMEWORKS, get_llm_service
from sqlalchemy.orm import selectinload


async def get_analysis_run_by_id(
    db: AsyncSession,
    run_id: str,
    org_id: str,
) -> AnalysisRun | None:
    """Get an analysis run by ID."""
    result = await db.execute(
        select(AnalysisRun).where(
            AnalysisRun.id == run_id,
            AnalysisRun.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def get_analysis_runs(
    db: AsyncSession,
    org_id: str,
    document_id: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[AnalysisRun], int]:
    """List analysis runs with pagination."""
    query = select(AnalysisRun).where(AnalysisRun.organization_id == org_id)

    if document_id:
        query = query.where(AnalysisRun.document_id == document_id)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(AnalysisRun.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    runs = list(result.scalars().all())

    return runs, total


async def get_findings(
    db: AsyncSession,
    org_id: str,
    document_id: str | None = None,
    analysis_run_id: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Finding], int]:
    """List findings with pagination and filtering."""
    query = select(Finding).where(Finding.organization_id == org_id)

    if document_id:
        query = query.where(Finding.document_id == document_id)
    if analysis_run_id:
        query = query.where(Finding.analysis_run_id == analysis_run_id)
    if severity:
        query = query.where(Finding.severity == severity)
    if status:
        query = query.where(Finding.status == status)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate with PostgreSQL-compatible severity ordering
    severity_order = case(
        (Finding.severity == "critical", 1),
        (Finding.severity == "high", 2),
        (Finding.severity == "medium", 3),
        (Finding.severity == "low", 4),
        (Finding.severity == "info", 5),
        else_=6,
    )
    query = query.order_by(
        severity_order,
        Finding.created_at.desc(),
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    findings = list(result.scalars().all())

    return findings, total


async def get_finding_by_id(
    db: AsyncSession,
    finding_id: str,
    org_id: str,
) -> Finding | None:
    """Get a finding by ID."""
    result = await db.execute(
        select(Finding).where(
            Finding.id == finding_id,
            Finding.organization_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def update_finding(
    db: AsyncSession,
    finding_id: str,
    org_id: str,
    update_data: dict,
) -> Finding | None:
    """Update a finding."""
    finding = await get_finding_by_id(db, finding_id, org_id)
    if not finding:
        return None

    for field, value in update_data.items():
        if value is not None:
            setattr(finding, field, value)

    # Track resolution
    if update_data.get("status") in ["remediated", "accepted", "false_positive"]:
        finding.resolved_at = datetime.now(UTC)

    await db.flush()
    await db.refresh(finding)
    return finding


def _validate_severity(severity: str) -> str:
    """Validate and normalize severity level.

    Args:
        severity: The severity string from LLM response

    Returns:
        Validated severity string (defaults to 'medium' if invalid)
    """
    valid_severities = {s.value for s in FindingSeverity}
    severity_lower = severity.lower().strip() if severity else "medium"

    if severity_lower in valid_severities:
        return severity_lower

    # Handle common variations
    severity_mapping = {
        "crit": "critical",
        "hi": "high",
        "med": "medium",
        "lo": "low",
        "informational": "info",
        "information": "info",
    }

    return severity_mapping.get(severity_lower, "medium")


def _extract_citation_from_evidence(
    evidence: dict[str, Any] | str | None,
    chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """Extract citation details from evidence data.

    Args:
        evidence: Evidence from LLM (dict with excerpt_number, page, quote or string)
        chunks: List of chunk data for cross-referencing

    Returns:
        Dict with chunk_id, page_number, section_header, quoted_text
    """
    citation = {
        "chunk_id": None,
        "page_number": None,
        "section_header": None,
        "quoted_text": None,
    }

    if not evidence:
        return citation

    # Handle string evidence (just the quote)
    if isinstance(evidence, str):
        citation["quoted_text"] = evidence
        return citation

    # Handle dict evidence
    if isinstance(evidence, dict):
        citation["quoted_text"] = evidence.get("quoted_text") or evidence.get("quote")
        citation["page_number"] = evidence.get("page_number") or evidence.get("page")
        citation["section_header"] = evidence.get("section_header") or evidence.get(
            "section"
        )

        # Try to find the referenced chunk
        excerpt_num = evidence.get("excerpt_number")
        if excerpt_num is not None and 0 < excerpt_num <= len(chunks):
            chunk = chunks[excerpt_num - 1]  # excerpt_number is 1-indexed
            citation["chunk_id"] = chunk.get("id")
            if not citation["page_number"]:
                citation["page_number"] = chunk.get("page_number")
            if not citation["section_header"]:
                citation["section_header"] = chunk.get("section_header")

    return citation


def _get_framework_control_mapping(framework_id: str) -> dict[str, dict[str, Any]]:
    """Build a mapping of control IDs to control details for a framework.

    Args:
        framework_id: The framework identifier

    Returns:
        Dict mapping control_id -> {name, description, category_id}
    """
    controls = get_framework_controls(framework_id)
    if not controls:
        return {}

    mapping = {}
    for control in controls:
        mapping[control.id] = {
            "name": control.name,
            "description": control.description,
            "category_id": control.category_id,
            "requirements": [
                {"id": r.id, "description": r.description, "guidance": r.guidance}
                for r in control.requirements
            ],
        }

    return mapping


def _validate_framework_control(
    control_id: str | None,
    control_mapping: dict[str, dict[str, Any]],
    framework_id: str,
) -> str | None:
    """Validate that a framework control exists and normalize the ID.

    Args:
        control_id: The control ID from LLM response
        control_mapping: Mapping of valid control IDs
        framework_id: The framework being analyzed

    Returns:
        Validated control ID or None if not valid
    """
    if not control_id:
        return None

    # Direct match
    if control_id in control_mapping:
        return control_id

    # Try case-insensitive match
    control_upper = control_id.upper()
    for valid_id in control_mapping:
        if valid_id.upper() == control_upper:
            return valid_id

    # Try partial match (e.g., "CC6.1" might be written as "CC6.1.1")
    for valid_id in control_mapping:
        if control_id.startswith(valid_id) or valid_id.startswith(control_id):
            return valid_id

    # Return original if no match found (might be a valid control not in our data)
    return control_id


async def run_analysis(
    db: AsyncSession,
    document_id: str,
    org_id: str,
    framework: str,
    chunk_limit: int = 50,
    focus_controls: list[str] | None = None,
    custom_framework_id: str | None = None,
) -> AnalysisRun:
    """Run enhanced compliance analysis on a document.

    This function performs RAG-based analysis using:
    - Structured compliance framework data for accurate control mapping
    - Enhanced prompts for detailed finding generation
    - Page-specific citations from document chunks

    When custom_framework_id is provided the analysis runs against the user-defined
    controls from that framework instead of a built-in one.

    Args:
        db: Database session
        document_id: Document to analyze
        org_id: Organization ID
        framework: Compliance framework key or 'custom'
        chunk_limit: Maximum chunks to analyze
        focus_controls: Optional list of specific control IDs to focus on
        custom_framework_id: UUID of a CustomFramework to use instead of built-in

    Returns:
        AnalysisRun with detailed findings

    Raises:
        ValueError: If document not found or analysis fails
    """
    # Resolve custom framework or validate built-in
    custom_fw = None
    if custom_framework_id:
        fw_result = await db.execute(
            select(CustomFramework)
            .where(
                CustomFramework.id == custom_framework_id,
                CustomFramework.organization_id == org_id,
                CustomFramework.is_active == True,  # noqa: E712
            )
            .options(selectinload(CustomFramework.controls))
        )
        custom_fw = fw_result.scalar_one_or_none()
        if not custom_fw:
            raise ValueError("Custom framework not found")
        if not custom_fw.controls:
            raise ValueError("Custom framework has no controls — add at least one control before running analysis")
        # Use a unique framework label so findings are traceable
        framework = f"custom:{custom_fw.name}"
    elif framework not in SUPPORTED_FRAMEWORKS:
        raise ValueError(f"Unsupported framework: {framework}")

    # Get document
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.organization_id == org_id,
        )
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise ValueError("Document not found")

    if not document.is_processed:
        raise ValueError("Document must be processed before analysis")

    # Get LLM service (supports Anthropic Claude and Google Gemini)
    llm_service = get_llm_service()
    if not llm_service.is_configured:
        raise ValueError("LLM service not configured - check API keys")

    # Load framework controls for prompt context
    if custom_fw:
        framework_summary = None
        control_mapping = {}
        # Serialise custom controls into the same shape the prompt builder expects
        controls_for_prompt = [
            {
                "id": ctrl.control_id,
                "name": ctrl.name,
                "description": ctrl.description,
                "category": ctrl.category or "",
                "guidance": ctrl.guidance or "",
            }
            for ctrl in custom_fw.controls
        ]
    else:
        framework_summary = get_framework_summary(framework)
        control_mapping = _get_framework_control_mapping(framework)
        controls_for_prompt = None
        if focus_controls:
            controls_for_prompt = [
                {"id": ctrl_id, **control_mapping[ctrl_id]}
                for ctrl_id in focus_controls
                if ctrl_id in control_mapping
            ]
        elif control_mapping:
            sample_controls = list(control_mapping.items())[:15]
            controls_for_prompt = [
                {"id": ctrl_id, **details} for ctrl_id, details in sample_controls
            ]

    # Create analysis run
    analysis_run = AnalysisRun(
        organization_id=org_id,
        document_id=document_id,
        framework=framework,
        model_used=llm_service.model,
        status="running",
        started_at=datetime.now(UTC),
    )
    db.add(analysis_run)
    await db.flush()

    try:
        # Get document chunks
        chunks_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(chunk_limit)
        )
        chunks = list(chunks_result.scalars().all())

        if not chunks:
            raise ValueError("Document has no chunks to analyze")

        analysis_run.chunks_analyzed = len(chunks)

        # Prepare chunks for analysis with full metadata
        chunk_data = [
            {
                "id": chunk.id,
                "content": chunk.content,
                "section_header": chunk.section_header,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]

        # Build enhanced document context
        document_context = build_chunk_context(chunk_data, include_metadata=True)

        # Build the compliance analysis prompt with framework controls
        analysis_prompt = build_compliance_analysis_prompt(
            document_context=document_context,
            framework_id=framework,
            document_type=document.document_type or "security_document",
            controls=controls_for_prompt,
        )

        # Run analysis with enhanced prompt
        result = await llm_service.analyze_document_with_prompt(
            prompt=analysis_prompt,
            framework=framework,
            document_type=document.document_type,
        )

        # Update metrics
        analysis_run.input_tokens = result.input_tokens
        analysis_run.output_tokens = result.output_tokens
        analysis_run.summary = result.summary

        # Create findings with enhanced citation data
        findings_created = 0
        for finding_data in result.findings:
            # Validate and normalize severity
            severity = _validate_severity(finding_data.get("severity"))

            # Validate framework control
            framework_control = _validate_framework_control(
                finding_data.get("framework_control"),
                control_mapping,
                framework,
            )

            # Extract citation details
            evidence_data = finding_data.get("evidence")
            citation = _extract_citation_from_evidence(evidence_data, chunk_data)

            # Format evidence string (include quote and context)
            evidence_text = None
            if citation["quoted_text"]:
                evidence_parts = [f'"{citation["quoted_text"]}"']
                if citation["page_number"]:
                    evidence_parts.append(f"(Page {citation['page_number']})")
                evidence_text = " ".join(evidence_parts)
            elif isinstance(evidence_data, str):
                evidence_text = evidence_data

            # Build impact text
            impact_text = None
            impact_data = finding_data.get("impact")
            if isinstance(impact_data, dict):
                impact_text = impact_data.get("description", "")
                risk_scenarios = impact_data.get("risk_scenarios", [])
                if risk_scenarios:
                    impact_text += "\n\nRisk Scenarios:\n" + "\n".join(
                        f"- {s}" for s in risk_scenarios
                    )
            elif isinstance(impact_data, str):
                impact_text = impact_data

            # Build remediation text
            remediation_text = None
            remediation_data = finding_data.get("remediation")
            if isinstance(remediation_data, dict):
                remediation_text = remediation_data.get("summary", "")
                steps = remediation_data.get("detailed_steps") or remediation_data.get(
                    "steps", []
                )
                if steps:
                    remediation_text += "\n\nRemediation Steps:\n" + "\n".join(
                        f"{i}. {step}" for i, step in enumerate(steps, 1)
                    )
            elif isinstance(remediation_data, str):
                remediation_text = remediation_data

            # Create the finding with full citation data
            finding = Finding(
                analysis_run_id=analysis_run.id,
                document_id=document_id,
                organization_id=org_id,
                title=finding_data.get("title", "Untitled Finding")[:500],
                severity=severity,
                framework=framework,
                framework_control=framework_control,
                description=finding_data.get("description", ""),
                evidence=evidence_text,
                remediation=remediation_text,
                impact=impact_text,
                chunk_id=citation["chunk_id"],
                page_number=citation["page_number"],
                section_header=citation["section_header"],
                confidence_score=finding_data.get("confidence"),
            )
            db.add(finding)
            findings_created += 1

        analysis_run.findings_count = findings_created
        analysis_run.status = "completed"
        analysis_run.completed_at = datetime.now(UTC)

        # Add framework info to summary if available
        if framework_summary:
            analysis_run.summary = (
                f"Analysis against {framework_summary.name} "
                f"({framework_summary.control_count} controls). "
                f"{result.summary}"
            )

        await db.flush()
        await db.refresh(analysis_run)
        return analysis_run

    except Exception as e:
        analysis_run.status = "failed"
        analysis_run.error_message = str(e)
        analysis_run.completed_at = datetime.now(UTC)
        await db.flush()
        raise ValueError(f"Analysis failed: {e!s}") from e


async def run_targeted_analysis(
    db: AsyncSession,
    document_id: str,
    org_id: str,
    framework: str,
    control_ids: list[str],
    chunk_limit: int = 30,
) -> AnalysisRun:
    """Run targeted analysis focusing on specific controls.

    This is useful for deep-dive analysis on particular control areas
    or follow-up analysis after initial findings.

    Args:
        db: Database session
        document_id: Document to analyze
        org_id: Organization ID
        framework: Compliance framework
        control_ids: List of specific control IDs to analyze
        chunk_limit: Maximum chunks to analyze

    Returns:
        AnalysisRun with targeted findings

    Raises:
        ValueError: If document not found or analysis fails
    """
    return await run_analysis(
        db=db,
        document_id=document_id,
        org_id=org_id,
        framework=framework,
        chunk_limit=chunk_limit,
        focus_controls=control_ids,
    )


async def get_finding_summary(
    db: AsyncSession,
    org_id: str,
    document_id: str | None = None,
) -> dict:
    """Get summary of findings by severity and status."""
    query = select(Finding).where(Finding.organization_id == org_id)

    if document_id:
        query = query.where(Finding.document_id == document_id)

    result = await db.execute(query)
    findings = list(result.scalars().all())

    summary = {
        "total": len(findings),
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
        "open": 0,
        "resolved": 0,
    }

    for finding in findings:
        if finding.severity in summary:
            summary[finding.severity] += 1

        if finding.is_open:
            summary["open"] += 1
        else:
            summary["resolved"] += 1

    return summary
