FINANCE_REJECT_KEYWORDS = {
    "shares surge",
    "share price",
    "stock price",
    "market cap",
    "investor sentiment",
    "analyst rating",
    "analyst ratings",
    "eps",
    "quarterly earnings",
    "earnings beat",
    "earnings miss",
}

FINANCE_IMPACT_KEYWORDS = {
    "tax",
    "tariff",
    "tariffs",
    "customs",
    "transfer pricing",
    "incentive",
    "incentives",
    "import duty",
    "accounting standard",
    "withholding tax",
    "export control",
    "chip export",
}

SALES_OPPORTUNITY_KEYWORDS = {
    "casino opening",
    "new resort",
    "resort expansion",
    "gaming floor upgrade",
    "capex",
    "renovation",
    "procurement",
    "rfp",
    "table games expansion",
    "property development",
    "gaming license",
    "new casino",
    "smart table deployment",
    "table automation rollout",
}


def detect_sales_opportunity(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in SALES_OPPORTUNITY_KEYWORDS)
