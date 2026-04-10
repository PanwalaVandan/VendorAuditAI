"""Vendor auto-categorization service for intelligent vendor classification.

This module provides automatic vendor categorization based on keywords, service types,
and data access patterns. It recommends appropriate risk levels and compliance frameworks
based on the vendor's characteristics.

Based on research of enterprise vendor ecosystems (e.g., DoorDash, enterprise tech stacks).

Version: 2.0 - Expanded to 25 DoorDash-style vendor categories
Updated: January 2026
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskLevel(str, Enum):
    """Vendor risk levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AssessmentPriority(str, Enum):
    """Assessment priority levels."""

    IMMEDIATE = "immediate"  # Tier 1 - Critical vendors requiring immediate assessment
    STANDARD = "standard"  # Tier 2 - Important vendors with standard timeline
    DEFERRED = "deferred"  # Tier 3 - Lower priority vendors


class VendorCategory(str, Enum):
    """Standard vendor categories for classification - 25 DoorDash-style categories."""

    # Tier 1 - Critical Infrastructure
    CLOUD_INFRASTRUCTURE = "cloud_infrastructure"
    DATA_WAREHOUSE = "data_warehouse"
    PAYMENT_PROCESSING = "payment_processing"
    IDENTITY_ACCESS = "identity_access"

    # Tier 1-2 - High Priority
    AI_ML_PLATFORMS = "ai_ml_platforms"
    BACKGROUND_CHECK = "background_check"
    FRAUD_DETECTION = "fraud_detection"
    POS_INTEGRATION = "pos_integration"
    SECURITY_TOOLS = "security_tools"
    HEALTHCARE = "healthcare"

    # Tier 2 - Important
    ANALYTICS_BI = "analytics_bi"
    CUSTOMER_SUPPORT = "customer_support"
    MAPPING_LOGISTICS = "mapping_logistics"
    HR_WORKFORCE = "hr_workforce"
    MARKETING_ADVERTISING = "marketing_advertising"
    INSURANCE_RISK = "insurance_risk"
    AUTONOMOUS_ROBOTICS = "autonomous_robotics"

    # Tier 2-3 - Standard
    COMMUNICATION = "communication"
    DEVOPS_DEVELOPMENT = "devops_development"
    LEGAL_CONTRACT = "legal_contract"

    # Tier 3 - Lower Priority
    OFFICE_COLLABORATION = "office_collaboration"
    PHYSICAL_SECURITY = "physical_security"
    TAX_COMPLIANCE = "tax_compliance"
    FLEET_MANAGEMENT = "fleet_management"
    FOOD_SAFETY = "food_safety"

    # Catch-all
    OTHER = "other"


@dataclass
class CategoryDefinition:
    """Definition of a vendor category with classification rules."""

    category: VendorCategory
    display_name: str
    description: str
    keywords: list[str]
    risk_level: RiskLevel
    default_frameworks: list[str]
    data_types: list[str]
    assessment_priority: AssessmentPriority
    tier: str  # "Tier 1", "Tier 1-2", "Tier 2", "Tier 2-3", "Tier 3"
    regulatory_notes: str | None = None


# Vendor category definitions with classification rules - 25 DoorDash-style categories
CATEGORY_DEFINITIONS: dict[VendorCategory, CategoryDefinition] = {
    # ==========================================================================
    # TIER 1 - CRITICAL INFRASTRUCTURE
    # ==========================================================================
    VendorCategory.CLOUD_INFRASTRUCTURE: CategoryDefinition(
        category=VendorCategory.CLOUD_INFRASTRUCTURE,
        display_name="Cloud Infrastructure",
        description="Cloud hosting, compute, storage, networking, and infrastructure services",
        keywords=[
            "aws",
            "amazon web services",
            "azure",
            "microsoft azure",
            "gcp",
            "google cloud",
            "google cloud platform",
            "cloud",
            "hosting",
            "infrastructure",
            "compute",
            "storage",
            "cdn",
            "cloudflare",
            "akamai",
            "fastly",
            "kubernetes",
            "k8s",
            "docker",
            "container",
            "serverless",
            "lambda",
            "ec2",
            "s3",
            "iaas",
            "paas",
            "virtual machine",
            "vm",
            "vpc",
            "load balancer",
            "auto scaling",
            "elastic",
            "blob storage",
            "object storage",
            "digitalocean",
            "linode",
            "vultr",
            "heroku",
            "railway",
            "render",
            "fly.io",
            "vercel",
            "netlify",
            "edge computing",
        ],
        risk_level=RiskLevel.CRITICAL,
        default_frameworks=["soc2", "sig_2026", "iso_27001", "caiq"],
        data_types=["production_data", "infrastructure_config", "secrets", "credentials", "customer_data"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1",
        regulatory_notes="Foundation of all digital operations; breach impacts entire organization",
    ),
    VendorCategory.DATA_WAREHOUSE: CategoryDefinition(
        category=VendorCategory.DATA_WAREHOUSE,
        display_name="Data Warehouse & Streaming",
        description="Data warehousing, data lakes, streaming platforms, and data infrastructure",
        keywords=[
            "snowflake",
            "databricks",
            "kafka",
            "apache kafka",
            "pinot",
            "apache pinot",
            "druid",
            "clickhouse",
            "redshift",
            "bigquery",
            "data warehouse",
            "data lake",
            "lakehouse",
            "delta lake",
            "iceberg",
            "hudi",
            "streaming",
            "stream processing",
            "real-time analytics",
            "event streaming",
            "message queue",
            "rabbitmq",
            "pulsar",
            "kinesis",
            "data pipeline",
            "etl",
            "elt",
            "data integration",
            "fivetran",
            "airbyte",
            "stitch",
            "dbt",
            "data transformation",
            "data modeling",
            "confluent",
            "spark",
            "apache spark",
            "flink",
            "presto",
            "trino",
            "athena",
            "synapse",
        ],
        risk_level=RiskLevel.CRITICAL,
        default_frameworks=["soc2", "sig_2026", "iso_27001"],
        data_types=["customer_pii", "analytics_data", "business_intelligence", "aggregated_data", "raw_data"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1",
        regulatory_notes="Contains comprehensive customer and business data; primary target for data breaches",
    ),
    VendorCategory.PAYMENT_PROCESSING: CategoryDefinition(
        category=VendorCategory.PAYMENT_PROCESSING,
        display_name="Payment Processing",
        description="Payment gateways, merchant services, and financial transaction processing",
        keywords=[
            "stripe",
            "adyen",
            "braintree",
            "marqeta",
            "payment",
            "payment gateway",
            "payment processing",
            "merchant services",
            "credit card",
            "debit card",
            "card processing",
            "pci",
            "pci dss",
            "pci scope",
            "checkout",
            "point of sale",
            "acquiring",
            "issuing",
            "card network",
            "visa",
            "mastercard",
            "amex",
            "discover",
            "ach",
            "wire transfer",
            "digital wallet",
            "apple pay",
            "google pay",
            "paypal",
            "square",
            "clover",
            "worldpay",
            "fiserv",
            "global payments",
            "chase paymentech",
            "authorize.net",
            "cybersource",
            "checkout.com",
            "mollie",
            "klarna",
            "afterpay",
            "affirm",
            "bnpl",
            "buy now pay later",
        ],
        risk_level=RiskLevel.CRITICAL,
        default_frameworks=["pci_dss", "soc2", "sig_2026", "soc1"],
        data_types=["pci", "payment_data", "card_data", "financial_transactions", "pii"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1",
        regulatory_notes="PCI DSS scope; financial fraud risk; requires annual PCI compliance validation",
    ),
    VendorCategory.IDENTITY_ACCESS: CategoryDefinition(
        category=VendorCategory.IDENTITY_ACCESS,
        display_name="Identity & Access Management",
        description="Authentication, authorization, SSO, and privileged access management",
        keywords=[
            "okta",
            "auth0",
            "cyberark",
            "duo",
            "duo security",
            "sso",
            "single sign-on",
            "identity",
            "iam",
            "authentication",
            "authorization",
            "onelogin",
            "ping identity",
            "azure ad",
            "entra id",
            "microsoft entra",
            "saml",
            "oauth",
            "oidc",
            "openid connect",
            "mfa",
            "multi-factor",
            "2fa",
            "two-factor",
            "passwordless",
            "passkey",
            "fido",
            "webauthn",
            "biometric",
            "pam",
            "privileged access",
            "beyondtrust",
            "delinea",
            "thycotic",
            "secret server",
            "vault",
            "hashicorp vault",
            "secrets management",
            "certificate management",
            "pki",
            "directory services",
            "ldap",
            "active directory",
            "identity governance",
            "access review",
            "sailpoint",
            "saviynt",
        ],
        risk_level=RiskLevel.CRITICAL,
        default_frameworks=["soc2", "sig_2026", "nist_csf", "iso_27001"],
        data_types=["credentials", "user_identities", "access_tokens", "secrets", "certificates"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1",
        regulatory_notes="Keys to the kingdom; compromise enables lateral movement across all systems",
    ),
    # ==========================================================================
    # TIER 1-2 - HIGH PRIORITY
    # ==========================================================================
    VendorCategory.AI_ML_PLATFORMS: CategoryDefinition(
        category=VendorCategory.AI_ML_PLATFORMS,
        display_name="AI & ML Platforms",
        description="Artificial intelligence, machine learning, LLM providers, and AI infrastructure",
        keywords=[
            "anthropic",
            "claude",
            "openai",
            "gpt",
            "chatgpt",
            "bedrock",
            "amazon bedrock",
            "sagemaker",
            "aws sagemaker",
            "ai",
            "artificial intelligence",
            "ml",
            "machine learning",
            "llm",
            "large language model",
            "foundation model",
            "generative ai",
            "genai",
            "google ai",
            "gemini",
            "vertex ai",
            "palm",
            "cohere",
            "hugging face",
            "replicate",
            "together ai",
            "anyscale",
            "modal",
            "nlp",
            "natural language",
            "computer vision",
            "deep learning",
            "neural network",
            "model training",
            "model inference",
            "fine-tuning",
            "embeddings",
            "vector database",
            "pinecone",
            "weaviate",
            "milvus",
            "chroma",
            "rag",
            "retrieval augmented",
            "copilot",
            "ai assistant",
            "mistral",
            "llama",
            "stable diffusion",
            "midjourney",
            "dall-e",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["nist_ai_rmf", "soc2", "sig_2026", "iso_27001"],
        data_types=["prompts", "training_data", "model_outputs", "embeddings", "pii"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1-2",
        regulatory_notes="Emerging AI governance requirements; data retention and training concerns",
    ),
    VendorCategory.BACKGROUND_CHECK: CategoryDefinition(
        category=VendorCategory.BACKGROUND_CHECK,
        display_name="Background Check & Verification",
        description="Background screening, identity verification, and pre-employment checks",
        keywords=[
            "checkr",
            "sterling",
            "hireright",
            "jumio",
            "background check",
            "background screening",
            "criminal background",
            "employment verification",
            "identity verification",
            "kyc",
            "know your customer",
            "aml",
            "anti-money laundering",
            "id verification",
            "document verification",
            "first advantage",
            "accurate background",
            "goodhire",
            "certn",
            "persona",
            "onfido",
            "veriff",
            "socure",
            "alloy",
            "plaid identity",
            "driver screening",
            "mvr",
            "motor vehicle records",
            "drug screening",
            "employment history",
            "education verification",
            "professional license",
            "reference check",
            "social security",
            "ssn verification",
            "e-verify",
            "i-9",
            "fcra",
            "fair credit",
            "consumer report",
            "pre-employment",
            "tenant screening",
        ],
        risk_level=RiskLevel.CRITICAL,
        default_frameworks=["soc2", "sig_2026", "fcra"],
        data_types=["pii", "ssn", "criminal_records", "employment_history", "fcra_data"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1",
        regulatory_notes="FCRA regulated; requires permissible purpose; adverse action requirements",
    ),
    VendorCategory.FRAUD_DETECTION: CategoryDefinition(
        category=VendorCategory.FRAUD_DETECTION,
        display_name="Fraud Detection & Prevention",
        description="Fraud prevention, risk scoring, and transaction monitoring",
        keywords=[
            "sift",
            "forter",
            "incognia",
            "riskified",
            "fraud",
            "fraud detection",
            "fraud prevention",
            "risk scoring",
            "risk assessment",
            "transaction monitoring",
            "anomaly detection",
            "device fingerprint",
            "device intelligence",
            "behavioral analytics",
            "bot detection",
            "account takeover",
            "ato",
            "chargeback",
            "dispute management",
            "kount",
            "signifyd",
            "ravelin",
            "feedzai",
            "nice actimize",
            "fico",
            "threat detection",
            "velocity checks",
            "geolocation",
            "ip reputation",
            "email risk",
            "phone risk",
            "synthetic identity",
            "promo abuse",
            "loyalty fraud",
            "refund abuse",
            "payment fraud",
            "card testing",
            "carding",
            "machine learning fraud",
            "rules engine",
            "case management",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "pci_dss"],
        data_types=["transaction_data", "device_data", "behavioral_data", "pii", "payment_data"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1-2",
        regulatory_notes="Often in PCI scope; processes sensitive transaction and behavioral data",
    ),
    VendorCategory.POS_INTEGRATION: CategoryDefinition(
        category=VendorCategory.POS_INTEGRATION,
        display_name="POS & Restaurant Integration",
        description="Point of sale systems, restaurant technology, and order management",
        keywords=[
            "olo",
            "toast",
            "square",
            "chowly",
            "pos",
            "point of sale",
            "restaurant pos",
            "order management",
            "menu management",
            "kitchen display",
            "kds",
            "online ordering",
            "digital ordering",
            "restaurant tech",
            "hospitality tech",
            "revel",
            "lightspeed",
            "clover",
            "touchbistro",
            "upserve",
            "ncr",
            "oracle micros",
            "shift4",
            "heartland",
            "aloha",
            "hungerrush",
            "qu",
            "ordermark",
            "grubhub integration",
            "uber eats integration",
            "doordash integration",
            "delivery integration",
            "menu sync",
            "inventory management",
            "table management",
            "reservation",
            "opentable",
            "resy",
            "sevenrooms",
            "order throttling",
            "prep time",
            "merchant portal",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "pci_dss"],
        data_types=["order_data", "payment_data", "customer_data", "menu_data", "inventory_data"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1-2",
        regulatory_notes="Often handles payment data; critical for marketplace operations",
    ),
    VendorCategory.SECURITY_TOOLS: CategoryDefinition(
        category=VendorCategory.SECURITY_TOOLS,
        display_name="Security Tools & Platforms",
        description="Security monitoring, endpoint protection, vulnerability management, and CSPM",
        keywords=[
            "crowdstrike",
            "wiz",
            "splunk",
            "snyk",
            "edr",
            "endpoint detection",
            "xdr",
            "extended detection",
            "siem",
            "security information",
            "security monitoring",
            "firewall",
            "antivirus",
            "endpoint protection",
            "sentinelone",
            "palo alto",
            "zscaler",
            "elastic security",
            "qualys",
            "tenable",
            "rapid7",
            "veracode",
            "checkmarx",
            "sonarqube",
            "orca",
            "lacework",
            "prisma cloud",
            "vulnerability",
            "vulnerability scanning",
            "penetration test",
            "pentest",
            "bug bounty",
            "hackerone",
            "bugcrowd",
            "cspm",
            "cloud security",
            "sspm",
            "saas security",
            "threat intelligence",
            "soc",
            "security operations",
            "incident response",
            "dlp",
            "data loss prevention",
            "encryption",
            "key management",
            "kms",
            "hsm",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "nist_csf", "iso_27001"],
        data_types=["security_logs", "vulnerability_data", "endpoint_telemetry", "threat_data", "credentials"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1-2",
        regulatory_notes="Access to sensitive security data; potential for privilege escalation",
    ),
    VendorCategory.HEALTHCARE: CategoryDefinition(
        category=VendorCategory.HEALTHCARE,
        display_name="Healthcare & Medical",
        description="Healthcare systems, telehealth, EHR, and medical services",
        keywords=[
            "epic",
            "cerner",
            "oracle health",
            "telehealth",
            "healthcare",
            "health",
            "medical",
            "hipaa",
            "phi",
            "protected health",
            "ehr",
            "electronic health record",
            "emr",
            "electronic medical record",
            "telemedicine",
            "virtual care",
            "patient portal",
            "pharmacy",
            "prescription",
            "e-prescribe",
            "clinical",
            "patient",
            "doctor",
            "hospital",
            "health insurance",
            "medical claims",
            "allscripts",
            "meditech",
            "athenahealth",
            "veradigm",
            "teladoc",
            "amwell",
            "mdlive",
            "doxy.me",
            "zoom for healthcare",
            "health api",
            "fhir",
            "hl7",
            "healthcare analytics",
            "medical device",
            "iot health",
            "remote monitoring",
            "wellness",
            "mental health",
            "behavioral health",
        ],
        risk_level=RiskLevel.CRITICAL,
        default_frameworks=["hipaa", "soc2", "sig_2026", "hitrust"],
        data_types=["phi", "medical_records", "health_data", "prescription_data", "insurance_data"],
        assessment_priority=AssessmentPriority.IMMEDIATE,
        tier="Tier 1",
        regulatory_notes="HIPAA regulated; requires BAA; significant breach notification requirements",
    ),
    # ==========================================================================
    # TIER 2 - IMPORTANT
    # ==========================================================================
    VendorCategory.ANALYTICS_BI: CategoryDefinition(
        category=VendorCategory.ANALYTICS_BI,
        display_name="Analytics & Business Intelligence",
        description="Business intelligence, product analytics, and data visualization",
        keywords=[
            "sigma",
            "sigma computing",
            "amplitude",
            "mixpanel",
            "tableau",
            "analytics",
            "bi",
            "business intelligence",
            "data visualization",
            "dashboard",
            "reporting",
            "looker",
            "power bi",
            "metabase",
            "mode",
            "thoughtspot",
            "sisense",
            "qlik",
            "domo",
            "product analytics",
            "user analytics",
            "behavior analytics",
            "segment",
            "heap",
            "fullstory",
            "hotjar",
            "posthog",
            "pendo",
            "walkme",
            "gainsight",
            "customer analytics",
            "cohort analysis",
            "funnel analysis",
            "retention analysis",
            "a/b testing",
            "experimentation",
            "optimizely",
            "launchdarkly",
            "statsig",
            "split.io",
            "kpi",
            "metrics",
            "data studio",
            "looker studio",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "iso_27001"],
        data_types=["customer_data", "analytics_data", "behavioral_data", "aggregated_data", "pii"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="Access to customer behavioral data; privacy considerations for tracking",
    ),
    VendorCategory.CUSTOMER_SUPPORT: CategoryDefinition(
        category=VendorCategory.CUSTOMER_SUPPORT,
        display_name="Customer Support & CRM",
        description="Customer support platforms, helpdesk, ticketing, and CRM systems",
        keywords=[
            "zendesk",
            "salesforce",
            "salesforce service",
            "freshdesk",
            "intercom",
            "support",
            "helpdesk",
            "help desk",
            "ticketing",
            "customer service",
            "customer support",
            "crm",
            "customer relationship",
            "servicenow",
            "freshworks",
            "hubspot",
            "zoho",
            "kustomer",
            "gladly",
            "front",
            "help scout",
            "drift",
            "chatbot",
            "live chat",
            "chat support",
            "call center",
            "contact center",
            "ivr",
            "voicebot",
            "knowledge base",
            "faq",
            "self-service",
            "ticket management",
            "case management",
            "customer 360",
            "omnichannel",
            "customer experience",
            "cx platform",
            "nps",
            "csat",
            "customer feedback",
            "survey",
            "qualtrics",
            "medallia",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["support_tickets", "customer_info", "chat_logs", "pii", "communication_logs"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="Contains customer PII and communication history; potential for social engineering",
    ),
    VendorCategory.MAPPING_LOGISTICS: CategoryDefinition(
        category=VendorCategory.MAPPING_LOGISTICS,
        display_name="Mapping & Logistics",
        description="Mapping services, geolocation, routing, and logistics platforms",
        keywords=[
            "mapbox",
            "google maps",
            "here",
            "here technologies",
            "onfleet",
            "mapping",
            "maps",
            "geolocation",
            "geocoding",
            "routing",
            "directions",
            "navigation",
            "gps",
            "location",
            "location services",
            "logistics",
            "delivery routing",
            "last mile",
            "route optimization",
            "tomtom",
            "esri",
            "arcgis",
            "what3words",
            "radar",
            "bringg",
            "routific",
            "locus",
            "optimo route",
            "circuit",
            "track and trace",
            "real-time tracking",
            "eta",
            "estimated arrival",
            "dispatch",
            "dispatching",
            "delivery management",
            "driver tracking",
            "asset tracking",
            "geofencing",
            "places api",
            "search api",
            "map tiles",
            "satellite imagery",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["location_data", "route_info", "driver_data", "delivery_info", "customer_addresses"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="Location data has privacy implications; critical for delivery operations",
    ),
    VendorCategory.HR_WORKFORCE: CategoryDefinition(
        category=VendorCategory.HR_WORKFORCE,
        display_name="HR & Workforce Management",
        description="Human resources, payroll, recruiting, and workforce management",
        keywords=[
            "workday",
            "adp",
            "greenhouse",
            "lattice",
            "hr",
            "human resources",
            "hris",
            "hcm",
            "human capital",
            "recruiting",
            "recruitment",
            "ats",
            "applicant tracking",
            "payroll",
            "compensation",
            "benefits",
            "gusto",
            "rippling",
            "deel",
            "remote.com",
            "bamboohr",
            "namely",
            "zenefits",
            "paychex",
            "lever",
            "ashby",
            "gem",
            "linkedin recruiter",
            "indeed",
            "glassdoor",
            "employee",
            "onboarding",
            "offboarding",
            "performance",
            "performance review",
            "360 feedback",
            "learning management",
            "lms",
            "training",
            "culture amp",
            "15five",
            "betterworks",
            "workforce planning",
            "time tracking",
            "scheduling",
            "shift management",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "soc1"],
        data_types=["employee_pii", "payroll_data", "hr_records", "ssn", "compensation_data"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="Contains sensitive employee data; payroll requires SOC 1",
    ),
    VendorCategory.MARKETING_ADVERTISING: CategoryDefinition(
        category=VendorCategory.MARKETING_ADVERTISING,
        display_name="Marketing & Advertising",
        description="Marketing automation, advertising platforms, attribution, and campaigns",
        keywords=[
            "google ads",
            "meta",
            "meta ads",
            "facebook ads",
            "trade desk",
            "the trade desk",
            "branch",
            "branch.io",
            "marketing",
            "advertising",
            "ads",
            "ad tech",
            "adtech",
            "campaign",
            "hubspot",
            "marketo",
            "salesforce marketing",
            "pardot",
            "mailchimp",
            "klaviyo",
            "braze",
            "iterable",
            "customer.io",
            "linkedin ads",
            "twitter ads",
            "tiktok ads",
            "snapchat ads",
            "programmatic",
            "dsp",
            "demand side",
            "retargeting",
            "remarketing",
            "attribution",
            "mmp",
            "mobile measurement",
            "appsflyer",
            "adjust",
            "singular",
            "kochava",
            "conversion tracking",
            "pixel",
            "tag manager",
            "gtm",
            "utm",
            "seo",
            "sem",
            "content marketing",
            "influencer",
            "affiliate",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["customer_segments", "conversion_data", "ad_data", "behavioral_data", "contact_info"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="Privacy regulations (GDPR, CCPA) apply; cookie consent requirements",
    ),
    VendorCategory.INSURANCE_RISK: CategoryDefinition(
        category=VendorCategory.INSURANCE_RISK,
        display_name="Insurance & Risk Management",
        description="Insurance providers, risk management, and claims processing",
        keywords=[
            "zurich",
            "cover genius",
            "axis",
            "axis capital",
            "insurance",
            "insurer",
            "insurance provider",
            "risk management",
            "underwriting",
            "claims",
            "claims processing",
            "policy management",
            "commercial insurance",
            "liability insurance",
            "workers comp",
            "workers compensation",
            "general liability",
            "professional liability",
            "e&o",
            "d&o",
            "cyber insurance",
            "auto insurance",
            "property insurance",
            "cargo insurance",
            "excess liability",
            "umbrella insurance",
            "certificate of insurance",
            "coi",
            "insurance verification",
            "loss prevention",
            "risk assessment",
            "actuarial",
            "reinsurance",
            "insurtech",
            "parametric insurance",
            "embedded insurance",
            "aig",
            "chubb",
            "travelers",
            "liberty mutual",
            "nationwide",
            "state farm",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026", "soc1"],
        data_types=["insurance_data", "claims_data", "pii", "financial_data", "risk_assessments"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="State insurance regulations apply; claims data is sensitive",
    ),
    VendorCategory.AUTONOMOUS_ROBOTICS: CategoryDefinition(
        category=VendorCategory.AUTONOMOUS_ROBOTICS,
        display_name="Autonomous Vehicles & Robotics",
        description="Autonomous delivery, robotics, drones, and autonomous vehicle technology",
        keywords=[
            "starship",
            "starship technologies",
            "serve",
            "serve robotics",
            "nuro",
            "zipline",
            "autonomous",
            "autonomous vehicle",
            "av",
            "self-driving",
            "robotics",
            "robot delivery",
            "delivery robot",
            "drone",
            "drone delivery",
            "uav",
            "unmanned aerial",
            "sidewalk robot",
            "last mile robot",
            "autonomous delivery",
            "waymo",
            "cruise",
            "motional",
            "aurora",
            "argo ai",
            "gatik",
            "einride",
            "kiwibot",
            "coco",
            "refraction ai",
            "udelv",
            "wing",
            "amazon prime air",
            "computer vision",
            "lidar",
            "sensor fusion",
            "path planning",
            "obstacle detection",
            "teleoperation",
            "remote operation",
            "fleet management",
            "robot fleet",
            "safety driver",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "iso_27001"],
        data_types=["location_data", "sensor_data", "video_data", "telemetry", "operational_data"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2",
        regulatory_notes="Emerging regulatory landscape; safety and liability considerations",
    ),
    # ==========================================================================
    # TIER 2-3 - STANDARD
    # ==========================================================================
    VendorCategory.COMMUNICATION: CategoryDefinition(
        category=VendorCategory.COMMUNICATION,
        display_name="Communication & Messaging",
        description="SMS, email, push notifications, and customer communication platforms",
        keywords=[
            "twilio",
            "sendgrid",
            "braze",
            "onesignal",
            "sms",
            "text message",
            "email",
            "email delivery",
            "transactional email",
            "marketing email",
            "voice",
            "voip",
            "messaging",
            "notification",
            "push notification",
            "in-app messaging",
            "vonage",
            "plivo",
            "bandwidth",
            "messagebird",
            "mailgun",
            "postmark",
            "amazon ses",
            "sparkpost",
            "customer.io",
            "iterable",
            "klaviyo",
            "attentive",
            "podium",
            "sms marketing",
            "a2p",
            "application to person",
            "10dlc",
            "short code",
            "toll-free",
            "two-way sms",
            "conversational messaging",
            "whatsapp business",
            "messenger",
            "rich messaging",
            "rcs",
            "mms",
            "otp",
            "verification sms",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["contact_info", "message_content", "communication_logs", "phone_numbers", "email_addresses"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2-3",
        regulatory_notes="TCPA compliance for SMS; CAN-SPAM for email; carrier compliance required",
    ),
    VendorCategory.DEVOPS_DEVELOPMENT: CategoryDefinition(
        category=VendorCategory.DEVOPS_DEVELOPMENT,
        display_name="DevOps & Development",
        description="Development tools, CI/CD, monitoring, and observability platforms",
        keywords=[
            "github",
            "terraform",
            "pagerduty",
            "datadog",
            "gitlab",
            "bitbucket",
            "jira",
            "confluence",
            "devops",
            "ci/cd",
            "continuous integration",
            "continuous deployment",
            "jenkins",
            "circleci",
            "travis",
            "github actions",
            "buildkite",
            "ansible",
            "puppet",
            "chef",
            "kubernetes",
            "helm",
            "argocd",
            "opsgenie",
            "victorops",
            "incident management",
            "on-call",
            "new relic",
            "dynatrace",
            "apm",
            "application performance",
            "monitoring",
            "observability",
            "logging",
            "tracing",
            "metrics",
            "grafana",
            "prometheus",
            "elastic",
            "elasticsearch",
            "kibana",
            "logstash",
            "sumo logic",
            "chronosphere",
            "honeycomb",
            "lightstep",
        ],
        risk_level=RiskLevel.HIGH,
        default_frameworks=["soc2", "sig_2026", "caiq"],
        data_types=["source_code", "secrets", "build_artifacts", "logs", "traces"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2-3",
        regulatory_notes="Access to source code and secrets; supply chain security considerations",
    ),
    VendorCategory.LEGAL_CONTRACT: CategoryDefinition(
        category=VendorCategory.LEGAL_CONTRACT,
        display_name="Legal & Contract Management",
        description="E-signature, contract lifecycle management, and legal tech",
        keywords=[
            "docusign",
            "ironclad",
            "icertis",
            "e-signature",
            "electronic signature",
            "esign",
            "digital signature",
            "contract management",
            "clm",
            "contract lifecycle",
            "legal tech",
            "legaltech",
            "contract automation",
            "adobe sign",
            "hellosign",
            "pandadoc",
            "signnow",
            "signrequest",
            "concord",
            "agiloft",
            "conga",
            "apttus",
            "document management",
            "document automation",
            "nda",
            "agreement",
            "legal document",
            "clause library",
            "redlining",
            "contract review",
            "contract analysis",
            "obligation management",
            "renewal management",
            "legal workflow",
            "matter management",
            "e-billing",
            "legal billing",
            "legal hold",
            "ediscovery",
            "relativity",
            "logikcull",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["contracts", "legal_documents", "signatures", "pii", "business_terms"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Tier 2-3",
        regulatory_notes="E-signature regulations (ESIGN Act, eIDAS); document retention requirements",
    ),
    # ==========================================================================
    # TIER 3 - LOWER PRIORITY
    # ==========================================================================
    VendorCategory.OFFICE_COLLABORATION: CategoryDefinition(
        category=VendorCategory.OFFICE_COLLABORATION,
        display_name="Office & Collaboration",
        description="Productivity suites, communication, and collaboration tools",
        keywords=[
            "google workspace",
            "g suite",
            "slack",
            "zoom",
            "notion",
            "office 365",
            "microsoft 365",
            "microsoft teams",
            "teams",
            "outlook",
            "gmail",
            "google drive",
            "onedrive",
            "sharepoint",
            "dropbox",
            "box",
            "asana",
            "monday.com",
            "trello",
            "basecamp",
            "clickup",
            "airtable",
            "coda",
            "miro",
            "figma",
            "canva",
            "lucidchart",
            "draw.io",
            "webex",
            "meet",
            "google meet",
            "video conferencing",
            "screen sharing",
            "collaboration",
            "productivity",
            "calendar",
            "scheduling",
            "calendly",
            "doodle",
            "project management",
            "task management",
            "wiki",
            "intranet",
            "employee communication",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["documents", "communications", "files", "calendar_data", "employee_data"],
        assessment_priority=AssessmentPriority.DEFERRED,
        tier="Tier 3",
        regulatory_notes="Data residency considerations; DLP policies recommended",
    ),
    VendorCategory.PHYSICAL_SECURITY: CategoryDefinition(
        category=VendorCategory.PHYSICAL_SECURITY,
        display_name="Physical Security",
        description="Physical access control, video surveillance, and building security",
        keywords=[
            "verkada",
            "kastle",
            "openpath",
            "physical security",
            "access control",
            "badge access",
            "key card",
            "visitor management",
            "video surveillance",
            "cctv",
            "security camera",
            "nvr",
            "dvr",
            "alarm system",
            "intrusion detection",
            "envoy",
            "greetly",
            "teem",
            "robin",
            "proxyclick",
            "brivo",
            "genetec",
            "milestone",
            "axis communications",
            "hikvision",
            "dahua",
            "lenel",
            "ccure",
            "s2",
            "software house",
            "door access",
            "turnstile",
            "biometric access",
            "facial recognition",
            "guard management",
            "patrol management",
            "incident reporting",
            "mass notification",
            "emergency notification",
            "building automation",
            "smart building",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["video_data", "access_logs", "visitor_data", "biometric_data", "location_data"],
        assessment_priority=AssessmentPriority.DEFERRED,
        tier="Tier 3",
        regulatory_notes="BIPA and biometric regulations; video retention policies required",
    ),
    VendorCategory.TAX_COMPLIANCE: CategoryDefinition(
        category=VendorCategory.TAX_COMPLIANCE,
        display_name="Tax & Compliance",
        description="Tax filing, mileage tracking, and regulatory compliance for gig workers",
        keywords=[
            "everlance",
            "stride",
            "taxbandits",
            "tax",
            "tax filing",
            "tax compliance",
            "1099",
            "w-2",
            "1099-k",
            "1099-nec",
            "tax reporting",
            "tax forms",
            "mileage tracking",
            "expense tracking",
            "deduction",
            "tax deduction",
            "quarterly taxes",
            "estimated taxes",
            "self-employment tax",
            "gig economy",
            "gig worker",
            "independent contractor",
            "freelancer tax",
            "turbotax",
            "h&r block",
            "taxact",
            "avalara",
            "vertex",
            "sovos",
            "sales tax",
            "vat",
            "tax automation",
            "tax calculation",
            "tax exemption",
            "tax certificate",
            "w-9",
            "tin verification",
            "ein",
            "itin",
            "irs compliance",
            "state tax",
            "payroll tax",
            "withholding",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026", "soc1"],
        data_types=["tax_data", "ssn", "ein", "financial_data", "income_data"],
        assessment_priority=AssessmentPriority.DEFERRED,
        tier="Tier 3",
        regulatory_notes="IRS reporting requirements; state tax nexus considerations",
    ),
    VendorCategory.FLEET_MANAGEMENT: CategoryDefinition(
        category=VendorCategory.FLEET_MANAGEMENT,
        display_name="Fleet Management",
        description="Vehicle tracking, fleet operations, and driver management",
        keywords=[
            "samsara",
            "geotab",
            "motive",
            "keeptruckin",
            "fleet",
            "fleet management",
            "vehicle tracking",
            "gps tracking",
            "telematics",
            "eld",
            "electronic logging",
            "hours of service",
            "hos",
            "driver management",
            "driver safety",
            "dash cam",
            "dashcam",
            "driver coaching",
            "driver scoring",
            "fuel management",
            "fuel card",
            "maintenance",
            "preventive maintenance",
            "dvir",
            "vehicle inspection",
            "asset tracking",
            "trailer tracking",
            "cold chain",
            "temperature monitoring",
            "route compliance",
            "ifta",
            "fuel tax",
            "verizon connect",
            "teletrac navman",
            "gps trackit",
            "fleet complete",
            "azuga",
            "zubie",
            "bouncie",
            "spireon",
            "calamp",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["location_data", "driver_data", "vehicle_data", "video_data", "telemetry"],
        assessment_priority=AssessmentPriority.DEFERRED,
        tier="Tier 3",
        regulatory_notes="ELD mandate compliance; FMCSA regulations; driver privacy considerations",
    ),
    VendorCategory.FOOD_SAFETY: CategoryDefinition(
        category=VendorCategory.FOOD_SAFETY,
        display_name="Food Safety & Quality",
        description="Food safety compliance, quality management, and supply chain traceability",
        keywords=[
            "foodlogiQ",
            "squadle",
            "compliancemetrix",
            "food safety",
            "haccp",
            "fsma",
            "food quality",
            "food compliance",
            "temperature monitoring",
            "cold chain",
            "food traceability",
            "supply chain traceability",
            "lot tracking",
            "recall management",
            "supplier management",
            "vendor qualification",
            "audit management",
            "corrective action",
            "capa",
            "sop management",
            "standard operating procedure",
            "food labeling",
            "allergen management",
            "ingredient management",
            "recipe management",
            "nutrition labeling",
            "food testing",
            "lab management",
            "lims",
            "certificate of analysis",
            "coa",
            "gfsi",
            "sqf",
            "brc",
            "ifs",
            "organic certification",
            "non-gmo",
            "food fraud",
            "adulteration",
            "zenput",
            "jolt",
            "testo",
        ],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["compliance_data", "audit_data", "supplier_data", "temperature_logs", "certification_data"],
        assessment_priority=AssessmentPriority.DEFERRED,
        tier="Tier 3",
        regulatory_notes="FDA/FSMA compliance; state health department requirements; recall liability",
    ),
    # ==========================================================================
    # CATCH-ALL
    # ==========================================================================
    VendorCategory.OTHER: CategoryDefinition(
        category=VendorCategory.OTHER,
        display_name="Other",
        description="Vendors that don't fit into standard categories",
        keywords=[],
        risk_level=RiskLevel.MEDIUM,
        default_frameworks=["soc2", "sig_2026"],
        data_types=["varies"],
        assessment_priority=AssessmentPriority.STANDARD,
        tier="Uncategorized",
        regulatory_notes=None,
    ),
}


@dataclass
class CategorizationResult:
    """Result of vendor categorization analysis."""

    primary_category: VendorCategory
    confidence: float
    risk_level: RiskLevel
    recommended_frameworks: list[str]
    matched_keywords: list[str]
    secondary_categories: list[VendorCategory]
    data_types: list[str]
    assessment_priority: str  # "immediate", "standard", "deferred"
    tier: str  # "Tier 1", "Tier 1-2", "Tier 2", "Tier 2-3", "Tier 3"
    regulatory_notes: str | None


def categorize_vendor(
    vendor_name: str,
    vendor_description: str | None = None,
    service_type: str | None = None,
    additional_context: str | None = None,
) -> CategorizationResult:
    """Automatically categorize a vendor based on available information.

    Args:
        vendor_name: Name of the vendor
        vendor_description: Optional description of the vendor/service
        service_type: Optional type of service provided
        additional_context: Any additional context about the vendor

    Returns:
        CategorizationResult with category, risk level, and recommended frameworks
    """
    # Combine all available text for analysis
    search_text = " ".join(
        filter(None, [vendor_name, vendor_description, service_type, additional_context])
    ).lower()

    # Score each category based on keyword matches
    category_scores: dict[VendorCategory, tuple[float, list[str]]] = {}

    for category, definition in CATEGORY_DEFINITIONS.items():
        if category == VendorCategory.OTHER:
            continue

        matches: list[str] = []
        for keyword in definition.keywords:
            if keyword.lower() in search_text:
                matches.append(keyword)

        if matches:
            # Score based on number of unique matches and keyword specificity
            score = len(matches) + (len(set(matches)) * 0.5)
            category_scores[category] = (score, matches)

    if not category_scores:
        # No matches found, default to OTHER
        other_def = CATEGORY_DEFINITIONS[VendorCategory.OTHER]
        return CategorizationResult(
            primary_category=VendorCategory.OTHER,
            confidence=0.3,
            risk_level=RiskLevel.MEDIUM,
            recommended_frameworks=["soc2", "sig_2026"],
            matched_keywords=[],
            secondary_categories=[],
            data_types=["unknown"],
            assessment_priority="standard",
            tier=other_def.tier,
            regulatory_notes=other_def.regulatory_notes,
        )

    # Sort categories by score
    sorted_categories = sorted(category_scores.items(), key=lambda x: x[1][0], reverse=True)

    primary_category = sorted_categories[0][0]
    primary_score, matched_keywords = sorted_categories[0][1]
    primary_definition = CATEGORY_DEFINITIONS[primary_category]

    # Calculate confidence based on score and uniqueness
    max_possible_score = len(primary_definition.keywords) * 1.5
    confidence = min(primary_score / max(max_possible_score, 1), 1.0)
    confidence = max(confidence, 0.4)  # Minimum confidence if we have matches

    # Get secondary categories (others with significant scores)
    secondary_categories = [
        cat for cat, (score, _) in sorted_categories[1:4] if score >= primary_score * 0.5
    ]

    # Use the assessment priority from the definition
    assessment_priority = primary_definition.assessment_priority.value

    return CategorizationResult(
        primary_category=primary_category,
        confidence=round(confidence, 2),
        risk_level=primary_definition.risk_level,
        recommended_frameworks=primary_definition.default_frameworks,
        matched_keywords=list(set(matched_keywords)),
        secondary_categories=secondary_categories,
        data_types=primary_definition.data_types,
        assessment_priority=assessment_priority,
        tier=primary_definition.tier,
        regulatory_notes=primary_definition.regulatory_notes,
    )


def get_framework_recommendations(
    category: VendorCategory,
    data_types: list[str] | None = None,
    is_eu_vendor: bool = False,
    is_financial_entity: bool = False,
    handles_student_data: bool = False,
    handles_health_data: bool = False,
    handles_payment_data: bool = False,
    handles_fcra_data: bool = False,
) -> list[str]:
    """Get framework recommendations based on vendor characteristics.

    Args:
        category: Primary vendor category
        data_types: Types of data the vendor processes
        is_eu_vendor: Whether the vendor operates in the EU
        is_financial_entity: Whether the vendor is a financial entity
        handles_student_data: Whether the vendor handles student data
        handles_health_data: Whether the vendor handles health data
        handles_payment_data: Whether the vendor handles payment/PCI data
        handles_fcra_data: Whether the vendor handles FCRA-regulated data

    Returns:
        List of recommended framework IDs
    """
    frameworks: list[str] = []

    # Get base recommendations from category
    if category in CATEGORY_DEFINITIONS:
        frameworks.extend(CATEGORY_DEFINITIONS[category].default_frameworks)

    # Add regulatory frameworks based on characteristics
    if is_eu_vendor or is_financial_entity:
        if "dora" not in frameworks:
            frameworks.append("dora")

    if handles_student_data:
        if "hecvat" not in frameworks:
            frameworks.insert(0, "hecvat")

    if handles_health_data:
        if "hipaa" not in frameworks:
            frameworks.insert(0, "hipaa")

    if handles_payment_data:
        if "pci_dss" not in frameworks:
            frameworks.insert(0, "pci_dss")

    if handles_fcra_data:
        if "fcra" not in frameworks:
            frameworks.insert(0, "fcra")

    # Ensure AI RMF is included for AI vendors
    if category == VendorCategory.AI_ML_PLATFORMS and "nist_ai_rmf" not in frameworks:
        frameworks.insert(0, "nist_ai_rmf")

    return list(dict.fromkeys(frameworks))  # Remove duplicates while preserving order


def get_category_info(category: VendorCategory) -> dict[str, Any]:
    """Get detailed information about a vendor category.

    Args:
        category: The vendor category

    Returns:
        Dictionary with category details
    """
    if category not in CATEGORY_DEFINITIONS:
        return {}

    definition = CATEGORY_DEFINITIONS[category]
    return {
        "id": definition.category.value,
        "display_name": definition.display_name,
        "description": definition.description,
        "risk_level": definition.risk_level.value,
        "default_frameworks": definition.default_frameworks,
        "typical_data_types": definition.data_types,
        "keyword_examples": definition.keywords[:15],  # First 15 keywords as examples
        "tier": definition.tier,
        "assessment_priority": definition.assessment_priority.value,
        "regulatory_notes": definition.regulatory_notes,
    }


def get_all_categories() -> list[dict[str, Any]]:
    """Get information about all available vendor categories.

    Returns:
        List of category information dictionaries
    """
    return [
        get_category_info(category)
        for category in VendorCategory
        if category != VendorCategory.OTHER
    ]


def get_categories_by_tier(tier: str) -> list[dict[str, Any]]:
    """Get all categories for a specific tier.

    Args:
        tier: Tier level ("Tier 1", "Tier 1-2", "Tier 2", "Tier 2-3", "Tier 3")

    Returns:
        List of category information dictionaries for the specified tier
    """
    return [
        get_category_info(category)
        for category, definition in CATEGORY_DEFINITIONS.items()
        if definition.tier == tier and category != VendorCategory.OTHER
    ]


# =============================================================================
# EXAMPLE VENDOR TAXONOMY
# Comprehensive database of 50+ example vendors including confirmed DoorDash vendors
# =============================================================================
EXAMPLE_VENDOR_TAXONOMY: dict[str, dict[str, Any]] = {
    # -------------------------------------------------------------------------
    # CLOUD INFRASTRUCTURE (Tier 1)
    # -------------------------------------------------------------------------
    "aws": {
        "name": "Amazon Web Services",
        "category": VendorCategory.CLOUD_INFRASTRUCTURE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Primary cloud infrastructure provider - compute, storage, networking",
        "data_access": ["full_production_data", "infrastructure_config", "secrets", "customer_data"],
        "frameworks": ["soc2", "soc1", "iso_27001", "fedramp", "pci_dss", "hipaa"],
        "tier": "Tier 1",
        "doordash_confirmed": True,
    },
    "gcp": {
        "name": "Google Cloud Platform",
        "category": VendorCategory.CLOUD_INFRASTRUCTURE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Cloud infrastructure, BigQuery, GKE, and AI services",
        "data_access": ["production_data", "analytics_data", "infrastructure_config"],
        "frameworks": ["soc2", "soc1", "iso_27001", "fedramp", "pci_dss"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "azure": {
        "name": "Microsoft Azure",
        "category": VendorCategory.CLOUD_INFRASTRUCTURE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Cloud infrastructure and enterprise services",
        "data_access": ["production_data", "infrastructure_config", "identity_data"],
        "frameworks": ["soc2", "soc1", "iso_27001", "fedramp", "pci_dss", "hipaa"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "cloudflare": {
        "name": "Cloudflare",
        "category": VendorCategory.CLOUD_INFRASTRUCTURE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "CDN, DDoS protection, edge computing, and security",
        "data_access": ["network_traffic", "request_logs", "ssl_certificates"],
        "frameworks": ["soc2", "iso_27001", "pci_dss"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # DATA WAREHOUSE (Tier 1)
    # -------------------------------------------------------------------------
    "snowflake": {
        "name": "Snowflake",
        "category": VendorCategory.DATA_WAREHOUSE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Cloud data warehouse platform",
        "data_access": ["customer_pii", "analytics_data", "business_data", "aggregated_metrics"],
        "frameworks": ["soc2", "soc1", "iso_27001", "hipaa", "pci_dss"],
        "tier": "Tier 1",
        "breach_history": "Affected by 2024 credential stuffing attacks via third-party tools",
        "doordash_confirmed": True,
    },
    "databricks": {
        "name": "Databricks",
        "category": VendorCategory.DATA_WAREHOUSE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Unified analytics platform - data engineering, ML, and analytics",
        "data_access": ["customer_data", "ml_training_data", "analytics_data"],
        "frameworks": ["soc2", "iso_27001", "hipaa"],
        "tier": "Tier 1",
        "doordash_confirmed": True,
    },
    "kafka": {
        "name": "Apache Kafka (Confluent)",
        "category": VendorCategory.DATA_WAREHOUSE,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Event streaming platform for real-time data pipelines",
        "data_access": ["event_data", "real_time_streams", "customer_events"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1",
        "doordash_confirmed": True,
    },
    "pinot": {
        "name": "Apache Pinot (StarTree)",
        "category": VendorCategory.DATA_WAREHOUSE,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Real-time OLAP datastore for user-facing analytics",
        "data_access": ["analytics_data", "real_time_metrics", "aggregated_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # PAYMENT PROCESSING (Tier 1)
    # -------------------------------------------------------------------------
    "stripe": {
        "name": "Stripe",
        "category": VendorCategory.PAYMENT_PROCESSING,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Payment processing, billing, and financial infrastructure",
        "data_access": ["payment_data", "pci_scope", "customer_financial_data"],
        "frameworks": ["pci_dss", "soc2", "soc1", "iso_27001"],
        "tier": "Tier 1",
        "doordash_confirmed": True,
    },
    "adyen": {
        "name": "Adyen",
        "category": VendorCategory.PAYMENT_PROCESSING,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Global payment platform for enterprise",
        "data_access": ["payment_data", "pci_scope", "transaction_data"],
        "frameworks": ["pci_dss", "soc2", "soc1"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "braintree": {
        "name": "Braintree (PayPal)",
        "category": VendorCategory.PAYMENT_PROCESSING,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Payment gateway and merchant services",
        "data_access": ["payment_data", "pci_scope"],
        "frameworks": ["pci_dss", "soc2", "soc1"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "marqeta": {
        "name": "Marqeta",
        "category": VendorCategory.PAYMENT_PROCESSING,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Modern card issuing platform",
        "data_access": ["card_data", "transaction_data", "pci_scope"],
        "frameworks": ["pci_dss", "soc2", "soc1"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # IDENTITY & ACCESS (Tier 1)
    # -------------------------------------------------------------------------
    "okta": {
        "name": "Okta",
        "category": VendorCategory.IDENTITY_ACCESS,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Enterprise identity and access management",
        "data_access": ["user_credentials", "access_tokens", "identity_data"],
        "frameworks": ["soc2", "iso_27001", "fedramp"],
        "tier": "Tier 1",
        "breach_history": "2023 support system breach; 2022 LAPSUS$ incident",
        "doordash_confirmed": False,
    },
    "auth0": {
        "name": "Auth0 (Okta)",
        "category": VendorCategory.IDENTITY_ACCESS,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Developer-focused identity platform",
        "data_access": ["user_credentials", "authentication_logs"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "cyberark": {
        "name": "CyberArk",
        "category": VendorCategory.IDENTITY_ACCESS,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Privileged access management",
        "data_access": ["privileged_credentials", "secrets", "session_recordings"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "duo": {
        "name": "Duo Security (Cisco)",
        "category": VendorCategory.IDENTITY_ACCESS,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Multi-factor authentication",
        "data_access": ["authentication_logs", "device_data", "user_data"],
        "frameworks": ["soc2", "iso_27001", "fedramp"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # AI & ML PLATFORMS (Tier 1-2)
    # -------------------------------------------------------------------------
    "anthropic": {
        "name": "Anthropic (Claude)",
        "category": VendorCategory.AI_ML_PLATFORMS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Claude AI assistant and API services",
        "data_access": ["prompts", "conversation_data", "api_requests"],
        "frameworks": ["soc2"],
        "tier": "Tier 1-2",
        "doordash_confirmed": True,
    },
    "openai": {
        "name": "OpenAI",
        "category": VendorCategory.AI_ML_PLATFORMS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "GPT models and AI API services",
        "data_access": ["prompts", "conversation_data", "training_potential"],
        "frameworks": ["soc2"],
        "tier": "Tier 1-2",
        "doordash_confirmed": True,
    },
    "bedrock": {
        "name": "Amazon Bedrock",
        "category": VendorCategory.AI_ML_PLATFORMS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "AWS managed foundation model service",
        "data_access": ["prompts", "model_outputs", "fine_tuning_data"],
        "frameworks": ["soc2", "iso_27001", "hipaa"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    "sagemaker": {
        "name": "Amazon SageMaker",
        "category": VendorCategory.AI_ML_PLATFORMS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "ML model training and deployment",
        "data_access": ["training_data", "model_artifacts", "inference_data"],
        "frameworks": ["soc2", "iso_27001", "hipaa"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # BACKGROUND CHECK (Tier 1)
    # -------------------------------------------------------------------------
    "checkr": {
        "name": "Checkr",
        "category": VendorCategory.BACKGROUND_CHECK,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Background check and screening platform",
        "data_access": ["ssn", "criminal_records", "employment_history", "pii"],
        "frameworks": ["soc2", "fcra"],
        "tier": "Tier 1",
        "regulatory_scope": "FCRA regulated",
        "doordash_confirmed": True,
    },
    "sterling": {
        "name": "Sterling",
        "category": VendorCategory.BACKGROUND_CHECK,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Enterprise background screening",
        "data_access": ["ssn", "criminal_records", "verification_data"],
        "frameworks": ["soc2", "fcra"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    "jumio": {
        "name": "Jumio",
        "category": VendorCategory.BACKGROUND_CHECK,
        "risk_level": RiskLevel.CRITICAL,
        "service_description": "Identity verification and eKYC",
        "data_access": ["identity_documents", "biometric_data", "pii"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # FRAUD DETECTION (Tier 1-2)
    # -------------------------------------------------------------------------
    "sift": {
        "name": "Sift",
        "category": VendorCategory.FRAUD_DETECTION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Digital trust and safety platform",
        "data_access": ["transaction_data", "device_data", "behavioral_data"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    "forter": {
        "name": "Forter",
        "category": VendorCategory.FRAUD_DETECTION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "E-commerce fraud prevention",
        "data_access": ["transaction_data", "identity_data", "device_fingerprints"],
        "frameworks": ["soc2", "pci_dss"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    "incognia": {
        "name": "Incognia",
        "category": VendorCategory.FRAUD_DETECTION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Location-based fraud prevention",
        "data_access": ["location_data", "device_data", "behavioral_patterns"],
        "frameworks": ["soc2"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # ANALYTICS & BI (Tier 2)
    # -------------------------------------------------------------------------
    "sigma": {
        "name": "Sigma Computing",
        "category": VendorCategory.ANALYTICS_BI,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Cloud-native business intelligence platform",
        "data_access": ["analytics_data", "business_metrics", "customer_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": True,
    },
    "amplitude": {
        "name": "Amplitude",
        "category": VendorCategory.ANALYTICS_BI,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Product analytics platform",
        "data_access": ["user_behavior", "product_metrics", "pii"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "mixpanel": {
        "name": "Mixpanel",
        "category": VendorCategory.ANALYTICS_BI,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Product analytics and user tracking",
        "data_access": ["user_events", "behavioral_data", "pii"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "tableau": {
        "name": "Tableau (Salesforce)",
        "category": VendorCategory.ANALYTICS_BI,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Data visualization and BI",
        "data_access": ["business_data", "analytics", "dashboards"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # CUSTOMER SUPPORT (Tier 2)
    # -------------------------------------------------------------------------
    "zendesk": {
        "name": "Zendesk",
        "category": VendorCategory.CUSTOMER_SUPPORT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Customer support and ticketing platform",
        "data_access": ["support_tickets", "customer_info", "chat_logs"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "salesforce": {
        "name": "Salesforce",
        "category": VendorCategory.CUSTOMER_SUPPORT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "CRM and customer service platform",
        "data_access": ["customer_data", "sales_data", "support_data"],
        "frameworks": ["soc2", "soc1", "iso_27001", "fedramp"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "intercom": {
        "name": "Intercom",
        "category": VendorCategory.CUSTOMER_SUPPORT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Customer messaging and engagement",
        "data_access": ["chat_logs", "customer_data", "behavioral_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # MAPPING & LOGISTICS (Tier 2)
    # -------------------------------------------------------------------------
    "mapbox": {
        "name": "Mapbox",
        "category": VendorCategory.MAPPING_LOGISTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Maps, navigation, and location services",
        "data_access": ["location_data", "route_data", "telemetry"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": True,
    },
    "google_maps": {
        "name": "Google Maps Platform",
        "category": VendorCategory.MAPPING_LOGISTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Mapping and routing services",
        "data_access": ["location_data", "route_info", "places_data"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "here": {
        "name": "HERE Technologies",
        "category": VendorCategory.MAPPING_LOGISTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Location platform and mapping services",
        "data_access": ["location_data", "routing_data", "traffic_data"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "onfleet": {
        "name": "Onfleet",
        "category": VendorCategory.MAPPING_LOGISTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Last-mile delivery management",
        "data_access": ["delivery_data", "driver_data", "customer_addresses"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # POS INTEGRATION (Tier 1-2)
    # -------------------------------------------------------------------------
    "olo": {
        "name": "Olo",
        "category": VendorCategory.POS_INTEGRATION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Restaurant ordering and delivery platform",
        "data_access": ["order_data", "menu_data", "customer_data"],
        "frameworks": ["soc2", "pci_dss"],
        "tier": "Tier 1-2",
        "doordash_confirmed": True,
    },
    "toast": {
        "name": "Toast",
        "category": VendorCategory.POS_INTEGRATION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Restaurant POS and management platform",
        "data_access": ["pos_data", "payment_data", "menu_data"],
        "frameworks": ["soc2", "pci_dss"],
        "tier": "Tier 1-2",
        "doordash_confirmed": True,
    },
    "square_pos": {
        "name": "Square",
        "category": VendorCategory.POS_INTEGRATION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "POS and payment processing",
        "data_access": ["pos_data", "payment_data", "customer_data"],
        "frameworks": ["soc2", "pci_dss"],
        "tier": "Tier 1-2",
        "doordash_confirmed": True,
    },
    "chowly": {
        "name": "Chowly",
        "category": VendorCategory.POS_INTEGRATION,
        "risk_level": RiskLevel.HIGH,
        "service_description": "POS integration for delivery platforms",
        "data_access": ["order_data", "menu_data", "integration_logs"],
        "frameworks": ["soc2"],
        "tier": "Tier 1-2",
        "doordash_confirmed": True,
    },
    # -------------------------------------------------------------------------
    # AUTONOMOUS & ROBOTICS (Tier 2)
    # -------------------------------------------------------------------------
    "starship": {
        "name": "Starship Technologies",
        "category": VendorCategory.AUTONOMOUS_ROBOTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Autonomous delivery robots",
        "data_access": ["location_data", "delivery_data", "sensor_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": True,
    },
    "serve_robotics": {
        "name": "Serve Robotics",
        "category": VendorCategory.AUTONOMOUS_ROBOTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Sidewalk delivery robots",
        "data_access": ["location_data", "video_data", "delivery_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": True,
    },
    "nuro": {
        "name": "Nuro",
        "category": VendorCategory.AUTONOMOUS_ROBOTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Autonomous delivery vehicles",
        "data_access": ["location_data", "sensor_data", "delivery_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "zipline": {
        "name": "Zipline",
        "category": VendorCategory.AUTONOMOUS_ROBOTICS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Drone delivery service",
        "data_access": ["delivery_data", "flight_data", "location_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # DEVOPS & DEVELOPMENT (Tier 2-3)
    # -------------------------------------------------------------------------
    "github": {
        "name": "GitHub",
        "category": VendorCategory.DEVOPS_DEVELOPMENT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Code hosting and collaboration",
        "data_access": ["source_code", "secrets", "ci_cd_logs"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    "terraform": {
        "name": "Terraform (HashiCorp)",
        "category": VendorCategory.DEVOPS_DEVELOPMENT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Infrastructure as code",
        "data_access": ["infrastructure_config", "state_files", "secrets"],
        "frameworks": ["soc2"],
        "tier": "Tier 2-3",
        "doordash_confirmed": True,
    },
    "pagerduty": {
        "name": "PagerDuty",
        "category": VendorCategory.DEVOPS_DEVELOPMENT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Incident management and on-call",
        "data_access": ["incident_data", "alert_logs", "on_call_schedules"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    "datadog": {
        "name": "Datadog",
        "category": VendorCategory.DEVOPS_DEVELOPMENT,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Monitoring and observability",
        "data_access": ["system_metrics", "logs", "traces", "apm_data"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # COMMUNICATION (Tier 2-3)
    # -------------------------------------------------------------------------
    "twilio": {
        "name": "Twilio",
        "category": VendorCategory.COMMUNICATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "SMS, voice, and messaging APIs",
        "data_access": ["phone_numbers", "message_content", "call_logs"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    "sendgrid": {
        "name": "SendGrid (Twilio)",
        "category": VendorCategory.COMMUNICATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Email delivery service",
        "data_access": ["email_content", "email_addresses", "delivery_logs"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    "braze": {
        "name": "Braze",
        "category": VendorCategory.COMMUNICATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Customer engagement platform",
        "data_access": ["customer_data", "behavioral_data", "campaign_data"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    "onesignal": {
        "name": "OneSignal",
        "category": VendorCategory.COMMUNICATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Push notification service",
        "data_access": ["device_tokens", "notification_content", "user_segments"],
        "frameworks": ["soc2"],
        "tier": "Tier 2-3",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # HR & WORKFORCE (Tier 2)
    # -------------------------------------------------------------------------
    "workday": {
        "name": "Workday",
        "category": VendorCategory.HR_WORKFORCE,
        "risk_level": RiskLevel.HIGH,
        "service_description": "HR and payroll system",
        "data_access": ["employee_pii", "payroll_data", "ssn"],
        "frameworks": ["soc2", "soc1"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "adp": {
        "name": "ADP",
        "category": VendorCategory.HR_WORKFORCE,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Payroll and HR services",
        "data_access": ["payroll_data", "employee_pii", "tax_data"],
        "frameworks": ["soc2", "soc1"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "greenhouse": {
        "name": "Greenhouse",
        "category": VendorCategory.HR_WORKFORCE,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Applicant tracking system",
        "data_access": ["candidate_pii", "interview_data", "hiring_decisions"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    "lattice": {
        "name": "Lattice",
        "category": VendorCategory.HR_WORKFORCE,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Performance management",
        "data_access": ["employee_data", "performance_reviews", "goals"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # SECURITY TOOLS (Tier 1-2)
    # -------------------------------------------------------------------------
    "crowdstrike": {
        "name": "CrowdStrike",
        "category": VendorCategory.SECURITY_TOOLS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Endpoint detection and response",
        "data_access": ["endpoint_telemetry", "security_events", "process_data"],
        "frameworks": ["soc2", "iso_27001", "fedramp"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    "wiz": {
        "name": "Wiz",
        "category": VendorCategory.SECURITY_TOOLS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Cloud security posture management",
        "data_access": ["cloud_config", "vulnerability_data", "security_findings"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    "splunk": {
        "name": "Splunk",
        "category": VendorCategory.SECURITY_TOOLS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "SIEM and log management",
        "data_access": ["security_logs", "system_logs", "event_data"],
        "frameworks": ["soc2", "iso_27001", "fedramp"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    "snyk": {
        "name": "Snyk",
        "category": VendorCategory.SECURITY_TOOLS,
        "risk_level": RiskLevel.HIGH,
        "service_description": "Developer security platform",
        "data_access": ["source_code", "dependency_data", "vulnerability_findings"],
        "frameworks": ["soc2", "iso_27001"],
        "tier": "Tier 1-2",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # OFFICE & COLLABORATION (Tier 3)
    # -------------------------------------------------------------------------
    "google_workspace": {
        "name": "Google Workspace",
        "category": VendorCategory.OFFICE_COLLABORATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Productivity suite and collaboration",
        "data_access": ["documents", "emails", "calendar_data"],
        "frameworks": ["soc2", "soc1", "iso_27001", "fedramp"],
        "tier": "Tier 3",
        "doordash_confirmed": False,
    },
    "slack": {
        "name": "Slack",
        "category": VendorCategory.OFFICE_COLLABORATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Team messaging and collaboration",
        "data_access": ["messages", "files", "channel_data"],
        "frameworks": ["soc2", "iso_27001", "fedramp"],
        "tier": "Tier 3",
        "doordash_confirmed": False,
    },
    "zoom": {
        "name": "Zoom",
        "category": VendorCategory.OFFICE_COLLABORATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Video conferencing",
        "data_access": ["meeting_recordings", "chat_logs", "participant_data"],
        "frameworks": ["soc2", "iso_27001", "fedramp"],
        "tier": "Tier 3",
        "doordash_confirmed": False,
    },
    "notion": {
        "name": "Notion",
        "category": VendorCategory.OFFICE_COLLABORATION,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Collaborative workspace and documentation",
        "data_access": ["documents", "databases", "team_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 3",
        "doordash_confirmed": False,
    },
    # -------------------------------------------------------------------------
    # THIRD-PARTY DATA PROVIDERS
    # -------------------------------------------------------------------------
    "yelp": {
        "name": "Yelp",
        "category": VendorCategory.ANALYTICS_BI,
        "risk_level": RiskLevel.MEDIUM,
        "service_description": "Business reviews and local search data",
        "data_access": ["review_data", "business_listings", "api_data"],
        "frameworks": ["soc2"],
        "tier": "Tier 2",
        "doordash_confirmed": True,
    },
}


def get_doordash_confirmed_vendors() -> list[dict[str, Any]]:
    """Get all vendors confirmed to be used by DoorDash.

    Returns:
        List of vendor information dictionaries for DoorDash-confirmed vendors
    """
    return [
        {"key": key, **vendor}
        for key, vendor in EXAMPLE_VENDOR_TAXONOMY.items()
        if vendor.get("doordash_confirmed", False)
    ]


def lookup_vendor(vendor_key: str) -> dict[str, Any] | None:
    """Look up a vendor by key in the taxonomy.

    Args:
        vendor_key: The vendor key (e.g., "aws", "stripe")

    Returns:
        Vendor information dictionary or None if not found
    """
    return EXAMPLE_VENDOR_TAXONOMY.get(vendor_key.lower())


def search_vendors(
    query: str,
    category: VendorCategory | None = None,
    risk_level: RiskLevel | None = None,
    tier: str | None = None,
) -> list[dict[str, Any]]:
    """Search vendors in the taxonomy.

    Args:
        query: Search query for vendor name or description
        category: Optional category filter
        risk_level: Optional risk level filter
        tier: Optional tier filter

    Returns:
        List of matching vendor information dictionaries
    """
    results = []
    query_lower = query.lower()

    for key, vendor in EXAMPLE_VENDOR_TAXONOMY.items():
        # Check query match
        name_match = query_lower in vendor["name"].lower()
        desc_match = query_lower in vendor.get("service_description", "").lower()
        key_match = query_lower in key.lower()

        if not (name_match or desc_match or key_match):
            continue

        # Apply filters
        if category and vendor["category"] != category:
            continue
        if risk_level and vendor["risk_level"] != risk_level:
            continue
        if tier and vendor.get("tier") != tier:
            continue

        results.append({"key": key, **vendor})

    return results
