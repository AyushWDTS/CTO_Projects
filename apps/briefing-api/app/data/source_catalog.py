from app.models.source import FetchMethod, SourceType
from app.schemas.source import SourceCreate

ALLOWED_SOURCE_CATEGORIES = {
    "ai",
    "aml",
    "automation",
    "casino_operations",
    "compliance",
    "computer_vision",
    "electronics",
    "gaming",
    "regulation",
    "semiconductors",
    "technology",
}

ALLOWED_SOURCE_REGIONS = {
    "Asia",
    "Australia",
    "Canada",
    "EU",
    "Global",
    "India",
    "Macau",
    "Philippines",
    "Singapore",
    "UK",
    "US",
}


SOURCE_CATALOG: dict[str, list[SourceCreate]] = {
    "ai_ml_and_computer_vision": [
        SourceCreate(
            name="MIT Technology Review AI",
            url="https://www.technologyreview.com/topic/artificial-intelligence/",
            rss_url="https://www.technologyreview.com/topic/artificial-intelligence/feed/",
            source_type=SourceType.NEWS_SITE,
            category="ai",
            region="Global",
            priority=1,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.90,
            notes="AI research and industry coverage relevant to WDTS product and R&D monitoring.",
        ),
        SourceCreate(
            name="VentureBeat AI",
            url="https://venturebeat.com/category/ai/",
            rss_url="https://venturebeat.com/category/ai/feed/",
            source_type=SourceType.NEWS_SITE,
            category="ai",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.80,
            notes="Enterprise AI and ML product news for WDTS technology scanning.",
        ),
        SourceCreate(
            name="The Verge AI",
            url="https://www.theverge.com/ai-artificial-intelligence",
            rss_url="https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
            source_type=SourceType.NEWS_SITE,
            category="ai",
            region="Global",
            priority=3,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.75,
            notes="Mainstream AI product and platform news for competitive and ecosystem awareness.",
        ),
        SourceCreate(
            name="NVIDIA Newsroom",
            url="https://nvidianews.nvidia.com/",
            rss_url="https://nvidianews.nvidia.com/releases.xml",
            source_type=SourceType.COMPANY_IR,
            category="computer_vision",
            region="Global",
            priority=1,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.90,
            notes="GPU, edge AI, and vision platform announcements relevant to casino CV workloads.",
        ),
        SourceCreate(
            name="IEEE Spectrum AI",
            url="https://spectrum.ieee.org/topic/artificial-intelligence/",
            source_type=SourceType.NEWS_SITE,
            category="ai",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes=(
                "Engineering-focused AI and automation coverage. Kept manual until a stable "
                "topic RSS feed is verified for automatic ingestion."
            ),
        ),
    ],
    "semiconductors_and_chips": [
        SourceCreate(
            name="SEMI",
            url="https://www.semi.org/",
            source_type=SourceType.OTHER,
            category="semiconductors",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.STATIC_HTML,
            fetch_frequency_minutes=1440,
            reliability_score=0.80,
            notes="Semiconductor industry association for chip supply and manufacturing context.",
        ),
        SourceCreate(
            name="Semiconductor Engineering",
            url="https://semiengineering.com/",
            rss_url="https://semiengineering.com/feed/",
            source_type=SourceType.NEWS_SITE,
            category="semiconductors",
            region="Global",
            priority=1,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.85,
            notes="Deep semiconductor process, packaging, and component supply coverage.",
        ),
        SourceCreate(
            name="EE Times",
            url="https://www.eetimes.com/",
            rss_url="https://www.eetimes.com/feed/",
            source_type=SourceType.NEWS_SITE,
            category="electronics",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.80,
            notes="Electronics and chip design news relevant to WDTS hardware supply chains.",
        ),
        SourceCreate(
            name="IPC",
            url="https://www.ipc.org/",
            source_type=SourceType.OTHER,
            category="electronics",
            region="Global",
            priority=3,
            fetch_method=FetchMethod.STATIC_HTML,
            fetch_frequency_minutes=1440,
            reliability_score=0.75,
            notes="Electronics manufacturing standards association for PCB and component context.",
        ),
        SourceCreate(
            name="NXP Newsroom",
            url="https://www.nxp.com/company/about-nxp/newsroom:NEWSROOM",
            source_type=SourceType.COMPANY_IR,
            category="semiconductors",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes=(
                "RFID and secure-connectivity chip vendor news relevant to casino chip tracking. "
                "Kept manual until a stable public RSS or listing extractor is confirmed."
            ),
        ),
    ],
    "casino_and_gaming_tech": [
        SourceCreate(
            name="CDC Gaming Reports",
            url="https://cdcgaming.com/",
            rss_url="https://cdcgaming.com/feed/",
            source_type=SourceType.NEWS_SITE,
            category="gaming",
            region="US",
            priority=2,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.80,
            notes="US casino market and gaming technology news for WDTS commercial context.",
        ),
        SourceCreate(
            name="GGRAsia",
            url="https://www.ggrasia.com/",
            rss_url="https://www.ggrasia.com/feed/",
            source_type=SourceType.NEWS_SITE,
            category="gaming",
            region="Asia",
            priority=2,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.80,
            notes="Asia casino and gaming technology news for regional market monitoring.",
        ),
        SourceCreate(
            name="Inside Asian Gaming",
            url="https://www.asgam.com/",
            rss_url="https://www.asgam.com/feed/",
            source_type=SourceType.NEWS_SITE,
            category="gaming",
            region="Asia",
            priority=2,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.80,
            notes="Asian gaming publication covering casino tech and operator deployments.",
        ),
        SourceCreate(
            name="Yogonet",
            url="https://www.yogonet.com/international/",
            rss_url="https://www.yogonet.com/international/rss.xml",
            source_type=SourceType.NEWS_SITE,
            category="gaming",
            region="Global",
            priority=3,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.70,
            notes="Global gaming news feed for casino technology and market signals.",
        ),
        SourceCreate(
            name="RFID Journal",
            url="https://www.rfidjournal.com/",
            rss_url="https://www.rfidjournal.com/category/news/feed/",
            source_type=SourceType.NEWS_SITE,
            category="technology",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.RSS,
            fetch_frequency_minutes=720,
            reliability_score=0.80,
            notes="RFID and related sensing news relevant to smart-table chip tracking.",
        ),
    ],
    "smart_table_suppliers_and_labs": [
        SourceCreate(
            name="Gaming Laboratories International (GLI)",
            url="https://gaminglabs.com/press-releases/",
            source_type=SourceType.OTHER,
            category="gaming",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.90,
            notes=(
                "Gaming certification lab press releases for smart-table and equipment "
                "compliance. Kept manual until listing extraction is verified."
            ),
        ),
        SourceCreate(
            name="BMM Testlabs",
            url="https://bmm.com/news/",
            source_type=SourceType.OTHER,
            category="gaming",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.90,
            notes=(
                "Independent gaming test lab news for certification signals relevant to "
                "smart table deployments. Kept manual until page extraction is confirmed."
            ),
        ),
        SourceCreate(
            name="TCSJOHNHUXLEY",
            url="https://www.tcsjohnhuxley.com/news/",
            source_type=SourceType.COMPANY_IR,
            category="gaming",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes=(
                "Smart-table / table-game technology supplier news. Kept manual until a "
                "stable machine-readable news feed is verified."
            ),
        ),
        SourceCreate(
            name="Tangam Systems",
            url="https://www.tangamgaming.com/news/",
            source_type=SourceType.COMPANY_IR,
            category="gaming",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes=(
                "Table-game optimization and analytics competitor news. Kept manual until "
                "press/news page parsing is validated."
            ),
        ),
        SourceCreate(
            name="Interblock",
            url="https://www.interblockgaming.com/news/",
            source_type=SourceType.COMPANY_IR,
            category="gaming",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes=(
                "Electronic table games competitor news. Kept manual until a stable public "
                "news listing is confirmed."
            ),
        ),
        SourceCreate(
            name="Zebra Technologies Newsroom",
            url="https://www.zebra.com/us/en/about-zebra/newsroom.html",
            source_type=SourceType.COMPANY_IR,
            category="automation",
            region="Global",
            priority=3,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.80,
            notes=(
                "Auto-ID, RFID, and industrial automation vendor news useful for casino "
                "floor sensing. Kept manual until feed verification."
            ),
        ),
    ],
    "competitors_and_operators": [
        SourceCreate(
            name="MGM Resorts Investor Relations",
            url="https://investors.mgmresorts.com/",
            source_type=SourceType.COMPANY_IR,
            category="casino_operations",
            region="US",
            priority=3,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes="Operator IR source for casino market and technology investment signals.",
        ),
        SourceCreate(
            name="Las Vegas Sands Investor Relations",
            url="https://investor.sands.com/",
            source_type=SourceType.COMPANY_IR,
            category="casino_operations",
            region="Global",
            priority=3,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes="Operator IR source for US and Asia casino strategy and capex signals.",
        ),
        SourceCreate(
            name="Light & Wonder Newsroom",
            url="https://www.lnw.com/newsroom",
            source_type=SourceType.COMPANY_IR,
            category="gaming",
            region="Global",
            priority=2,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.85,
            notes=(
                "Major gaming technology competitor newsroom. Kept manual until a stable "
                "public listing or RSS path is verified."
            ),
        ),
    ],
    "gaming_regulators_and_compliance": [
        SourceCreate(
            name="Nevada Gaming Control Board",
            url="https://gaming.nv.gov/",
            source_type=SourceType.REGULATOR,
            category="gaming",
            region="US",
            priority=1,
            fetch_method=FetchMethod.STATIC_HTML,
            fetch_frequency_minutes=1440,
            reliability_score=0.95,
            notes="Nevada gaming regulator for licensing and enforcement visibility.",
        ),
        SourceCreate(
            name="PAGCOR",
            url="https://www.pagcor.ph/",
            source_type=SourceType.REGULATOR,
            category="gaming",
            region="Philippines",
            priority=1,
            fetch_method=FetchMethod.STATIC_HTML,
            fetch_frequency_minutes=1440,
            reliability_score=0.90,
            notes="Philippine Amusement and Gaming Corporation regulatory source.",
        ),
        SourceCreate(
            name="UK Gambling Commission",
            url="https://www.gamblingcommission.gov.uk/news",
            source_type=SourceType.REGULATOR,
            category="gaming",
            region="UK",
            priority=1,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.95,
            notes=(
                "UK gambling regulator news. Kept manual until a targeted listing/detail "
                "extraction strategy exists."
            ),
        ),
        SourceCreate(
            name="FinCEN",
            url="https://www.fincen.gov/news/press-releases",
            source_type=SourceType.REGULATOR,
            category="aml",
            region="US",
            priority=2,
            fetch_method=FetchMethod.STATIC_HTML,
            fetch_frequency_minutes=1440,
            reliability_score=0.95,
            notes="US financial crime regulator press releases relevant to casino compliance.",
        ),
        SourceCreate(
            name="Office of the United States Trade Representative",
            url="https://ustr.gov/about-us/policy-offices/press-office",
            source_type=SourceType.GOVERNMENT,
            category="regulation",
            region="US",
            priority=3,
            fetch_method=FetchMethod.MANUAL,
            fetch_frequency_minutes=1440,
            reliability_score=0.90,
            notes=(
                "US trade policy and tariff press office for semiconductor and component "
                "supply risk. Kept manual until listing extraction is confirmed."
            ),
        ),
    ],
}

SOURCE_URL_MIGRATIONS: dict[str, list[str]] = {
    "https://www.gamblingcommission.gov.uk/news": [
        "https://www.gamblingcommission.gov.uk/",
    ],
    "https://www.fincen.gov/news/press-releases": [
        "https://www.fincen.gov/",
    ],
}


def all_catalog_sources() -> list[SourceCreate]:
    return [source for group in SOURCE_CATALOG.values() for source in group]


def validate_source_catalog(sources: list[SourceCreate] | None = None) -> None:
    source_list = sources or all_catalog_sources()
    urls: set[str] = set()
    rss_urls: set[str] = set()

    for source in source_list:
        if source.url in urls:
            raise ValueError(f"Duplicate source URL: {source.url}")
        urls.add(source.url)

        if source.rss_url:
            if source.rss_url in rss_urls:
                raise ValueError(f"Duplicate RSS URL: {source.rss_url}")
            rss_urls.add(source.rss_url)

        if source.fetch_method == FetchMethod.RSS and not source.rss_url:
            raise ValueError(f"RSS source is missing rss_url: {source.name}")
        if source.fetch_method != FetchMethod.RSS and source.rss_url:
            raise ValueError(f"Only RSS fetch_method may define rss_url: {source.name}")
        if source.category not in ALLOWED_SOURCE_CATEGORIES:
            raise ValueError(f"Unknown source category: {source.category}")
        if source.region not in ALLOWED_SOURCE_REGIONS:
            raise ValueError(f"Unknown source region: {source.region}")
        if not 1 <= source.priority <= 5:
            raise ValueError(f"Invalid source priority: {source.name}")
        if not 0 <= source.reliability_score <= 1:
            raise ValueError(f"Invalid source reliability score: {source.name}")
        if source.fetch_method == FetchMethod.MANUAL and not _has_meaningful_manual_notes(source):
            raise ValueError(f"Manual source is missing activation notes: {source.name}")


def _has_meaningful_manual_notes(source: SourceCreate) -> bool:
    notes = (source.notes or "").strip()
    return len(notes) >= 30
