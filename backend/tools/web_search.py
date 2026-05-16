"""Whitelisted web search tool — via Tavily, filtered to authoritative sport/medical/government domains.

The whitelist is the same trust model as our static PDF ingestion: we don't index
random web pages, only authoritative sources. The Verifier still checks the
Reasoner's claims against the snippets returned by this tool, so even if a
whitelisted domain has a misleading page, claims unsupported by the actual returned
text will be stripped.
"""
from __future__ import annotations

from urllib.parse import urlparse
from backend.config import settings

# Authoritative sources. Extend cautiously — every new domain widens the trust surface.
ALLOWED_DOMAINS = {
    # International sport federations & Olympic bodies
    "fifa.com", "uefa.com", "olympic.org", "ioc.olympic.org",
    "wada-ama.org",
    "unitedworldwrestling.org", "iwf.sport", "fivb.com",
    # Sports-science societies
    "nsca.com", "acsm.org",
    # Turkish government & federations
    "gsb.gov.tr",
    "tff.org",        # Türkiye Futbol Federasyonu
    "twf.gov.tr",     # Türkiye Güreş Federasyonu
    "thf.org.tr",     # Türkiye Halter Federasyonu
    "tvf.org.tr",     # Türkiye Voleybol Federasyonu
    "olimpiyat.org.tr",
    # Medical / public-health authorities
    "who.int", "cdc.gov", "nih.gov", "pubmed.ncbi.nlm.nih.gov",
    # Open-access sport-science journals
    "bjsm.bmj.com", "jissn.biomedcentral.com", "frontiersin.org",
    # National institutes
    "ais.gov.au",
}


def _domain_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == d or host.endswith("." + d) for d in ALLOWED_DOMAINS)


def search(query: str, language: str = "tr", max_results: int = 5) -> dict:
    """Tool entry point. Returns {results: [...], message: "..."}.

    If the whitelist filter drops everything, returns an empty list with a message
    so the Reasoner can fall back to "no verified source on this".
    """
    if not query:
        return {"results": [], "message": "empty query"}
    if not settings.tavily_api_key:
        return {"results": [], "message": "TAVILY_API_KEY not configured"}

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)

        # Tavily's `include_domains` is our primary filter. We re-filter the
        # response too, in case Tavily relaxes the constraint or returns
        # subdomains we didn't intend.
        raw = client.search(
            query=query,
            search_depth="advanced",
            include_domains=sorted(ALLOWED_DOMAINS),
            max_results=max(max_results, 5),  # ask for a few extras so post-filter has room
        )

        filtered = [
            r for r in raw.get("results", [])
            if _domain_allowed(r.get("url", ""))
        ][:max_results]

        if not filtered:
            return {
                "results": [],
                "message": "no trusted sources found for this query",
            }

        return {
            "results": [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": (r.get("content") or "")[:800],
                    "score": r.get("score"),
                }
                for r in filtered
            ],
            "message": f"{len(filtered)} trusted source(s) found",
        }
    except Exception as e:
        return {"results": [], "message": f"search error: {type(e).__name__}: {e}"}
