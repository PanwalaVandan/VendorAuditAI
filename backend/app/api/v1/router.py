"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    agents,
    ai_classification,
    analysis,
    analytics,
    custom_frameworks,
    approved_vendors,
    audit,
    auth,
    bpo,
    categorization,
    compliance,
    dashboard,
    documents,
    export,
    integrations,
    monitoring,
    organization,
    playbooks,
    query,
    remediation,
    risk,
    search,
    sso,
    vendors,
)

api_router = APIRouter()

# Include auth router
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Include vendors router
api_router.include_router(vendors.router, prefix="/vendors", tags=["Vendors"])

# Include documents router
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])

# Include search router
api_router.include_router(search.router, prefix="/search", tags=["Search"])

# Include analysis router
api_router.include_router(analysis.router, prefix="/analysis", tags=["Analysis"])

# Include query router
api_router.include_router(query.router, prefix="/query", tags=["Query"])

# Include dashboard router
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# Include analytics router
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# Include compliance frameworks router
api_router.include_router(
    compliance.router, prefix="/frameworks", tags=["Compliance Frameworks"]
)

# Include categorization router
api_router.include_router(
    categorization.router, prefix="/categorization", tags=["Vendor Categorization"]
)

# Include export router
api_router.include_router(export.router, prefix="/export", tags=["Export"])

# Include remediation router
api_router.include_router(
    remediation.router, prefix="/remediation", tags=["Remediation"]
)

# Include monitoring router
api_router.include_router(
    monitoring.router, prefix="/monitoring", tags=["Monitoring"]
)

# Include audit router
api_router.include_router(audit.router, prefix="/audit", tags=["Audit"])

# Include SSO router
api_router.include_router(sso.router, prefix="/sso", tags=["SSO"])

# Include agents router
api_router.include_router(agents.router, prefix="/agents", tags=["AI Agents"])

# Include risk scoring router
api_router.include_router(risk.router, prefix="/risk", tags=["Risk Scoring"])

# Include admin router
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Include playbooks router
api_router.include_router(
    playbooks.router, prefix="/playbooks", tags=["AI Governance Playbooks"]
)

# Include AI classification router
api_router.include_router(
    ai_classification.router, prefix="/ai-classification", tags=["AI Tool Classification"]
)

# Include approved vendors router
api_router.include_router(
    approved_vendors.router, prefix="/approved-vendors", tags=["Approved AI Vendors"]
)

# Include custom frameworks router
api_router.include_router(
    custom_frameworks.router, prefix="/custom-frameworks", tags=["Custom Frameworks"]
)

# Include BPO router
api_router.include_router(
    bpo.router, prefix="/bpo", tags=["BPO Risk Management"]
)

# Include integrations router
api_router.include_router(
    integrations.router, prefix="/integrations", tags=["Integration Hub"]
)

# Include organization settings router
api_router.include_router(
    organization.router, prefix="/organization", tags=["Organization"]
)


@api_router.get("/status", tags=["Status"])
async def api_status() -> dict:
    """Get API v1 status."""
    return {
        "api_version": "v1",
        "status": "operational",
        "endpoints": {
            "admin": "/api/v1/admin",
            "agents": "/api/v1/agents",
            "ai_classification": "/api/v1/ai-classification",
            "analysis": "/api/v1/analysis",
            "analysis_findings": "/api/v1/analysis/findings",
            "analytics": "/api/v1/analytics",
            "approved_vendors": "/api/v1/approved-vendors",
            "audit": "/api/v1/audit",
            "auth": "/api/v1/auth",
            "bpo": "/api/v1/bpo",
            "categorization": "/api/v1/categorization",
            "dashboard": "/api/v1/dashboard",
            "documents": "/api/v1/documents",
            "export": "/api/v1/export",
            "frameworks": "/api/v1/frameworks",
            "integrations": "/api/v1/integrations",
            "monitoring": "/api/v1/monitoring",
            "organization": "/api/v1/organization",
            "playbooks": "/api/v1/playbooks",
            "query": "/api/v1/query",
            "remediation": "/api/v1/remediation",
            "risk": "/api/v1/risk",
            "search": "/api/v1/search",
            "sso": "/api/v1/sso",
            "vendors": "/api/v1/vendors",
        },
    }
