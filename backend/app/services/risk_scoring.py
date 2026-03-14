"""Risk scoring service for calculating vendor risk scores.

This service implements a comprehensive risk scoring algorithm that considers:
- Number and severity of findings (critical=10, high=7, medium=4, low=1)
- Compliance coverage percentage
- Data classification sensitivity
- Vendor tier (critical=1.5x, high=1.3x, medium=1.0x, low=0.8x multiplier)
- Document freshness (older docs = higher risk)

Risk Score Ranges:
- 0-25: Low Risk (Green)
- 26-50: Medium Risk (Yellow)
- 51-75: High Risk (Orange)
- 76-100: Critical Risk (Red)
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document
from app.models.finding import Finding, FindingStatus
from app.models.vendor import Vendor
from app.schemas.risk import (
    RiskCalculationResponse,
    RiskFactor,
    RiskScore,
    RiskScoreListResponse,
    RiskTrend,
    RiskTrendPoint,
    RiskTrendsResponse,
)

logger = logging.getLogger(__name__)

# Severity weights for findings
SEVERITY_WEIGHTS = {
    "critical": 10,
    "high": 7,
    "medium": 4,
    "low": 1,
    "info": 0,
}

# Tier multipliers
TIER_MULTIPLIERS = {
    "critical": 1.5,
    "high": 1.3,
    "medium": 1.0,
    "low": 0.8,
}

# Data classification sensitivity weights
DATA_CLASSIFICATION_WEIGHTS = {
    "restricted": 1.5,
    "confidential": 1.3,
    "internal": 1.0,
    "public": 0.7,
    None: 1.0,
}

# Risk factor weights (must sum to 1.0)
FACTOR_WEIGHTS = {
    "findings": 0.40,       # 40% weight
    "compliance": 0.25,     # 25% weight
    "data_sensitivity": 0.15,  # 15% weight
    "document_freshness": 0.20,  # 20% weight
}

# Document age thresholds (days)
DOCUMENT_AGE_THRESHOLDS = {
    "fresh": 90,      # < 90 days = low risk
    "moderate": 180,  # 90-180 days = medium risk
    "stale": 365,     # 180-365 days = high risk
    # > 365 days = critical risk
}


def _get_risk_level(score: float) -> tuple[str, str]:
    """Convert a risk score to a risk level and color.

    Args:
        score: Risk score between 0-100

    Returns:
        Tuple of (risk_level, color)
    """
    if score <= 25:
        return "low", "green"
    elif score <= 50:
        return "medium", "yellow"
    elif score <= 75:
        return "high", "orange"
    else:
        return "critical", "red"


def _calculate_findings_score(
    findings: list[Finding],
) -> tuple[float, dict[str, int]]:
    """Calculate the findings-based risk score.

    Args:
        findings: List of Finding objects for the vendor

    Returns:
        Tuple of (score 0-100, severity counts dict)
    """
    counts = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    # Only count open findings
    open_findings = [
        f for f in findings
        if f.status == FindingStatus.OPEN.value or f.status == FindingStatus.ACKNOWLEDGED.value
    ]

    weighted_sum = 0
    for finding in open_findings:
        severity = finding.severity.lower() if finding.severity else "low"
        weight = SEVERITY_WEIGHTS.get(severity, 1)
        weighted_sum += weight
        if severity in counts:
            counts[severity] += 1

    # Normalize to 0-100 scale
    # Max expected: 10 critical findings = 100 points
    max_expected = 10 * SEVERITY_WEIGHTS["critical"]
    score = min(100, (weighted_sum / max_expected) * 100)

    return score, counts


def _calculate_compliance_score(
    documents: list[Document],
    findings: list[Finding],
) -> float:
    """Calculate compliance coverage score.

    Higher coverage = lower risk.

    Args:
        documents: List of documents for the vendor
        findings: List of findings for the vendor

    Returns:
        Risk score 0-100 (lower = better compliance)
    """
    if not documents:
        # No documents = high risk
        return 80.0

    # Count processed documents
    processed_docs = [d for d in documents if d.status == "processed"]
    if not processed_docs:
        return 70.0

    # Calculate coverage based on document types covered
    expected_doc_types = {"soc2", "iso27001", "pentest"}
    covered_types = {d.document_type for d in processed_docs}
    coverage_ratio = len(covered_types.intersection(expected_doc_types)) / len(expected_doc_types)

    # Factor in remediated findings
    total_findings = len(findings)
    remediated_findings = len([
        f for f in findings
        if f.status in [FindingStatus.REMEDIATED.value, FindingStatus.ACCEPTED.value]
    ])

    if total_findings > 0:
        remediation_ratio = remediated_findings / total_findings
    else:
        remediation_ratio = 1.0  # No findings = good

    # Combined score (inverse - higher coverage = lower risk)
    combined_coverage = (coverage_ratio * 0.6) + (remediation_ratio * 0.4)

    # Convert to risk score (0 = perfect coverage, 100 = no coverage)
    return max(0, 100 - (combined_coverage * 100))


def _calculate_data_sensitivity_score(
    data_classification: str | None,
    tier: str,
) -> float:
    """Calculate risk based on data sensitivity.

    Args:
        data_classification: Data classification level
        tier: Vendor tier

    Returns:
        Risk score 0-100
    """
    # Base score from data classification
    classification = data_classification.lower() if data_classification else None
    classification_weight = DATA_CLASSIFICATION_WEIGHTS.get(classification, 1.0)

    # Tier factor
    tier_mult = TIER_MULTIPLIERS.get(tier.lower() if tier else "medium", 1.0)

    # Base risk for data handling
    base_risk = 40.0  # Baseline data handling risk

    # Apply multipliers
    score = base_risk * classification_weight * tier_mult

    return min(100, score)


def _calculate_document_freshness_score(documents: list[Document]) -> tuple[float, int | None]:
    """Calculate risk based on document age.

    Older documents indicate potentially outdated compliance information.

    Args:
        documents: List of documents for the vendor

    Returns:
        Tuple of (risk score 0-100, oldest document age in days)
    """
    if not documents:
        return 90.0, None  # No documents = very high risk

    processed_docs = [d for d in documents if d.status == "processed"]
    if not processed_docs:
        return 85.0, None

    # Find oldest document
    now = datetime.now(timezone.utc)
    oldest_age_days = 0

    for doc in processed_docs:
        ts = doc.processed_at or doc.created_at
        if ts:
            # SQLite stores naive datetimes - treat as UTC for safe comparison
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            age = (now - ts).days
            oldest_age_days = max(oldest_age_days, age)

    # Score based on age thresholds
    if oldest_age_days <= DOCUMENT_AGE_THRESHOLDS["fresh"]:
        score = 10.0 + (oldest_age_days / DOCUMENT_AGE_THRESHOLDS["fresh"]) * 15
    elif oldest_age_days <= DOCUMENT_AGE_THRESHOLDS["moderate"]:
        score = 25.0 + ((oldest_age_days - DOCUMENT_AGE_THRESHOLDS["fresh"]) /
                        (DOCUMENT_AGE_THRESHOLDS["moderate"] - DOCUMENT_AGE_THRESHOLDS["fresh"])) * 25
    elif oldest_age_days <= DOCUMENT_AGE_THRESHOLDS["stale"]:
        score = 50.0 + ((oldest_age_days - DOCUMENT_AGE_THRESHOLDS["moderate"]) /
                        (DOCUMENT_AGE_THRESHOLDS["stale"] - DOCUMENT_AGE_THRESHOLDS["moderate"])) * 25
    else:
        score = 75.0 + min(25, (oldest_age_days - DOCUMENT_AGE_THRESHOLDS["stale"]) / 365 * 25)

    return min(100, score), oldest_age_days if oldest_age_days > 0 else None


async def calculate_vendor_risk_score(
    db: AsyncSession,
    vendor: Vendor,
) -> RiskScore:
    """Calculate comprehensive risk score for a single vendor.

    Args:
        db: Database session
        vendor: Vendor object to calculate risk for

    Returns:
        RiskScore with complete breakdown
    """
    # Get related data
    # Get findings for this vendor's documents
    findings_query = (
        select(Finding)
        .join(Document, Finding.document_id == Document.id)
        .where(Document.vendor_id == vendor.id)
    )
    result = await db.execute(findings_query)
    findings = list(result.scalars().all())

    # Get documents
    docs_query = select(Document).where(Document.vendor_id == vendor.id)
    result = await db.execute(docs_query)
    documents = list(result.scalars().all())

    # Calculate individual factor scores
    findings_raw, severity_counts = _calculate_findings_score(findings)
    compliance_raw = _calculate_compliance_score(documents, findings)
    data_sensitivity_raw = _calculate_data_sensitivity_score(
        vendor.data_classification, vendor.tier
    )
    freshness_raw, doc_age_days = _calculate_document_freshness_score(documents)

    # Apply tier multiplier to overall score
    tier_mult = TIER_MULTIPLIERS.get(vendor.tier.lower() if vendor.tier else "medium", 1.0)

    # Calculate weighted scores
    factors = [
        RiskFactor(
            name="Findings Risk",
            description="Risk based on number and severity of open compliance findings",
            raw_value=findings_raw,
            weighted_value=findings_raw * FACTOR_WEIGHTS["findings"],
            weight=FACTOR_WEIGHTS["findings"],
            max_possible=100 * FACTOR_WEIGHTS["findings"],
        ),
        RiskFactor(
            name="Compliance Coverage",
            description="Risk based on compliance documentation coverage and remediation progress",
            raw_value=compliance_raw,
            weighted_value=compliance_raw * FACTOR_WEIGHTS["compliance"],
            weight=FACTOR_WEIGHTS["compliance"],
            max_possible=100 * FACTOR_WEIGHTS["compliance"],
        ),
        RiskFactor(
            name="Data Sensitivity",
            description="Risk based on data classification and vendor criticality",
            raw_value=data_sensitivity_raw,
            weighted_value=data_sensitivity_raw * FACTOR_WEIGHTS["data_sensitivity"],
            weight=FACTOR_WEIGHTS["data_sensitivity"],
            max_possible=100 * FACTOR_WEIGHTS["data_sensitivity"],
        ),
        RiskFactor(
            name="Document Freshness",
            description="Risk based on age of compliance documentation",
            raw_value=freshness_raw,
            weighted_value=freshness_raw * FACTOR_WEIGHTS["document_freshness"],
            weight=FACTOR_WEIGHTS["document_freshness"],
            max_possible=100 * FACTOR_WEIGHTS["document_freshness"],
        ),
    ]

    # Calculate overall score
    base_score = sum(f.weighted_value for f in factors)

    # Apply tier multiplier (capped at 100)
    overall_score = min(100, base_score * tier_mult)

    # Get risk level
    risk_level, risk_color = _get_risk_level(overall_score)

    # Calculate compliance coverage percentage
    processed_docs = len([d for d in documents if d.status == "processed"])
    compliance_coverage = (processed_docs / max(len(documents), 1)) * 100 if documents else 0

    return RiskScore(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        overall_score=round(overall_score, 2),
        risk_level=risk_level,
        risk_color=risk_color,
        factors=factors,
        calculated_at=datetime.now(timezone.utc),
        findings_critical=severity_counts["critical"],
        findings_high=severity_counts["high"],
        findings_medium=severity_counts["medium"],
        findings_low=severity_counts["low"],
        total_findings=sum(severity_counts.values()),
        compliance_coverage=round(compliance_coverage, 2),
        vendor_tier=vendor.tier or "medium",
        data_classification=vendor.data_classification,
        document_age_days=doc_age_days,
    )


async def get_all_vendor_risk_scores(
    db: AsyncSession,
    org_id: str,
    skip: int = 0,
    limit: int = 100,
) -> RiskScoreListResponse:
    """Get risk scores for all vendors in an organization.

    Args:
        db: Database session
        org_id: Organization ID
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        RiskScoreListResponse with all vendor scores
    """
    # Get vendors
    query = (
        select(Vendor)
        .where(Vendor.organization_id == org_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    vendors = list(result.scalars().all())

    # Count total vendors
    count_query = (
        select(func.count(Vendor.id))
        .where(Vendor.organization_id == org_id)
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Calculate scores for all vendors
    scores = []
    for vendor in vendors:
        score = await calculate_vendor_risk_score(db, vendor)
        scores.append(score)

    # Calculate summary statistics
    if scores:
        avg_score = sum(s.overall_score for s in scores) / len(scores)
        high_risk_count = sum(
            1 for s in scores
            if s.risk_level in ["high", "critical"]
        )
    else:
        avg_score = 0
        high_risk_count = 0

    return RiskScoreListResponse(
        data=scores,
        total=total,
        average_score=round(avg_score, 2),
        high_risk_count=high_risk_count,
    )


async def get_vendor_risk_score(
    db: AsyncSession,
    vendor_id: str,
    org_id: str,
) -> RiskScore | None:
    """Get detailed risk score for a specific vendor.

    Args:
        db: Database session
        vendor_id: Vendor ID
        org_id: Organization ID

    Returns:
        RiskScore or None if vendor not found
    """
    query = (
        select(Vendor)
        .where(Vendor.id == vendor_id, Vendor.organization_id == org_id)
    )
    result = await db.execute(query)
    vendor = result.scalar_one_or_none()

    if not vendor:
        return None

    return await calculate_vendor_risk_score(db, vendor)


async def recalculate_risk_scores(
    db: AsyncSession,
    org_id: str,
    vendor_ids: list[str] | None = None,
    force: bool = False,
) -> RiskCalculationResponse:
    """Trigger risk recalculation for vendors.

    Args:
        db: Database session
        org_id: Organization ID
        vendor_ids: Optional list of specific vendor IDs to recalculate
        force: Force recalculation even if recently calculated

    Returns:
        RiskCalculationResponse with results
    """
    import time
    start_time = time.time()

    errors = []
    processed = 0

    # Build query
    if vendor_ids:
        query = (
            select(Vendor)
            .where(
                Vendor.organization_id == org_id,
                Vendor.id.in_(vendor_ids),
            )
        )
    else:
        query = select(Vendor).where(Vendor.organization_id == org_id)

    result = await db.execute(query)
    vendors = list(result.scalars().all())

    for vendor in vendors:
        try:
            # Check if recently calculated (within last hour) unless forced
            if not force and vendor.risk_calculated_at:
                time_since_calc = datetime.now(timezone.utc) - vendor.risk_calculated_at
                if time_since_calc < timedelta(hours=1):
                    continue

            # Calculate score
            score = await calculate_vendor_risk_score(db, vendor)

            # Update vendor record with cached score
            vendor.risk_score = score.overall_score
            vendor.risk_calculated_at = datetime.now(timezone.utc)

            processed += 1

        except Exception as e:
            logger.error(f"Error calculating risk for vendor {vendor.id}: {e}")
            errors.append(f"Vendor {vendor.id}: {str(e)}")

    # Commit changes
    await db.commit()

    elapsed_ms = (time.time() - start_time) * 1000

    return RiskCalculationResponse(
        vendors_processed=processed,
        calculation_time_ms=round(elapsed_ms, 2),
        errors=errors,
        message=f"Successfully recalculated risk scores for {processed} vendors",
    )


async def get_risk_trends(
    db: AsyncSession,
    org_id: str,
    days: int = 30,
) -> RiskTrendsResponse:
    """Get risk score trends over time for all vendors.

    Note: This is a simplified implementation that returns current scores.
    For full historical tracking, a separate risk_history table would be needed.

    Args:
        db: Database session
        org_id: Organization ID
        days: Number of days to look back

    Returns:
        RiskTrendsResponse with trend data
    """
    # Get all vendors with their current scores
    query = select(Vendor).where(Vendor.organization_id == org_id)
    result = await db.execute(query)
    vendors = list(result.scalars().all())

    trends = []
    total_change = 0

    for vendor in vendors:
        current_score = await calculate_vendor_risk_score(db, vendor)

        # Since we don't have historical data, simulate stable trend
        # In production, this would query a risk_history table
        history = [
            RiskTrendPoint(
                date=datetime.now(timezone.utc) - timedelta(days=days),
                score=current_score.overall_score,
                risk_level=current_score.risk_level,
            ),
            RiskTrendPoint(
                date=datetime.now(timezone.utc),
                score=current_score.overall_score,
                risk_level=current_score.risk_level,
            ),
        ]

        # Calculate trend direction (would be based on historical data)
        score_change = 0  # No change since we only have current data

        if score_change < -5:
            direction = "improving"
        elif score_change > 5:
            direction = "worsening"
        else:
            direction = "stable"

        trends.append(RiskTrend(
            vendor_id=vendor.id,
            vendor_name=vendor.name,
            current_score=current_score.overall_score,
            trend_direction=direction,
            score_change_30d=score_change,
            history=history,
        ))

        total_change += score_change

    # Calculate overall trend
    avg_change = total_change / len(vendors) if vendors else 0

    if avg_change < -5:
        overall_trend = "improving"
    elif avg_change > 5:
        overall_trend = "worsening"
    else:
        overall_trend = "stable"

    return RiskTrendsResponse(
        data=trends,
        total=len(trends),
        overall_trend=overall_trend,
        average_change_30d=round(avg_change, 2),
    )
