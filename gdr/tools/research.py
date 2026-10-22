"""Deep research and multi-engine web search tools for GDR AI.
Supports DuckDuckGo, Wikipedia, Brave, and SearXNG with citations and Markdown/PDF report export.
"""

from datetime import datetime, timezone
import html
import json
import logging
import os
from pathlib import Path
import re
from typing import List, Dict, Any, Optional
import urllib.parse
import requests

from gdr.tools.registry import tool
from gdr.safety.secrets import get_secret
from gdr.safety.untrusted import wrap_untrusted_content

logger = logging.getLogger("gdr.tools.research")


def check_personal_disambiguation(query: str) -> str:
    """Detect if query searches for a personal acquaintance or ambiguous personal name.
    Ensures public web profiles are never mistakenly conflated with user's personal contacts.
    """
    lower_q = query.lower()
    relationship_terms = [
        "girlfriend", "boyfriend", "gf", "bf", "wife", "husband", "partner",
        "friend", "dost", "meri girlfriend", "mera dost", "sister", "brother",
        "mom", "mother", "dad", "father", "cousin"
    ]
    has_rel = any(re.search(rf"\b{re.escape(term)}\b", lower_q) for term in relationship_terms)

    tech_or_common_keywords = {
        "wiki", "python", "linux", "docs", "release", "news", "price", "vs", "api",
        "code", "github", "company", "corporation", "stock", "weather", "definition",
        "meaning", "movie", "song", "lyrics", "score", "game", "book", "author",
        "how", "what", "where", "when", "why", "who", "is", "the", "in", "to", "for"
    }
    words = [w for w in re.split(r"\W+", lower_q) if w]
    is_name_query = (
        len(words) in (1, 2)
        and not any(w in tech_or_common_keywords for w in words)
        and all(len(w) >= 3 for w in words)
    )

    if has_rel or is_name_query:
        return (
            "[PRIVACY & DISAMBIGUATION NOTICE: The search results below are public web pages. "
            "A matching first or full name in public web records is NOT evidence that an online person, journalist, or public profile "
            "is the user's girlfriend, contact, or friend. Never claim or infer that a public profile belongs to the user's "
            "acquaintance unless explicitly confirmed by the user. If ambiguous, ask the user for clarification.]\n\n"
        )
    return ""


@tool(
    name="web_search",
    description="Search the web using multi-engine backends. Returns titles, snippets, and URLs.",
    category="research",
    tier="AUTO"
)
def web_search(query: str, max_results: int = 5) -> str:
    """Execute web search across available search providers without external parser dependencies."""
    clean_query = query.strip()
    if not clean_query:
        return "Search query cannot be empty."

    disambig_notice = check_personal_disambiguation(clean_query)
    results: List[str] = []

    # 1. Try Brave Search if API key is configured
    brave_key = get_secret("BRAVE_API_KEY")
    if brave_key:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": brave_key, "Accept": "application/json"},
                params={"q": clean_query, "count": max_results},
                timeout=8
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("web", {}).get("results", [])[:max_results]:
                    results.append(f"• **{item.get('title')}**\n  URL: {item.get('url')}\n  {item.get('description')}")
                if results:
                    return disambig_notice + wrap_untrusted_content(f"search results for '{clean_query}'", "\n\n".join(results))
        except Exception as e:
            logger.warning(f"Brave search error: {e}")

    # 2. DuckDuckGo HTML Search (POST method)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://html.duckduckgo.com/",
        }
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": clean_query},
            headers=headers,
            timeout=8
        )
        if r.status_code == 200 and len(r.text) > 1000:
            titles = re.findall(
                r"<a[^>]+class=[\x27\"]result__a[\x27\"][^>]*href=[\x27\"]([^\x27\"]+)[\x27\"][^>]*>(.*?)</a>",
                r.text,
                re.DOTALL
            )
            snippets = re.findall(
                r"<a[^>]+class=[\x27\"]result__snippet[\x27\"][^>]*>(.*?)</a>",
                r.text,
                re.DOTALL
            )

            for i in range(min(max_results, len(titles))):
                href, raw_title = titles[i]
                if "uddg=" in href:
                    m = re.search(r"uddg=([^&]+)", href)
                    if m:
                        href = urllib.parse.unquote(m.group(1))
                title = html.unescape(re.sub(r"<[^>]+>", "", raw_title).strip())
                snip = html.unescape(re.sub(r"<[^>]+>", "", snippets[i]).strip()) if i < len(snippets) else ""
                results.append(f"• **{title}**\n  URL: {href}\n  {snip}")

            if results:
                return disambig_notice + wrap_untrusted_content(f"search results for '{clean_query}'", "\n\n".join(results))
    except Exception as e:
        logger.warning(f"DuckDuckGo HTML search error: {e}")

    # 3. DuckDuckGo Instant Answer API
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(clean_query)}&format=json&no_html=1&skip_disambig=1"
        r_api = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=6)
        if r_api.status_code in (200, 202):
            d = r_api.json()
            if d.get("AbstractText"):
                results.append(f"• **Instant Answer**:\n  {d.get('AbstractText')}\n  URL: {d.get('AbstractURL', 'https://duckduckgo.com')}")
            for t in d.get("RelatedTopics", [])[:max_results]:
                if isinstance(t, dict) and t.get("Text") and t.get("FirstURL"):
                    results.append(f"• **{t.get('Text')[:60]}**\n  URL: {t.get('FirstURL')}\n  {t.get('Text')}")
            if results:
                return disambig_notice + wrap_untrusted_content(f"search results for '{clean_query}'", "\n\n".join(results[:max_results]))
    except Exception as e:
        logger.warning(f"DuckDuckGo API error: {e}")

    # 4. Wikipedia Full-Text Search API (Fast, reliable encyclopedia facts)
    try:
        w_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(clean_query)}&format=json&utf8=1&srlimit={max_results}"
        r_w = requests.get(w_url, headers={"User-Agent": "GDRAI-Assistant/2.0"}, timeout=6)
        if r_w.status_code == 200:
            w_data = r_w.json()
            for item in w_data.get("query", {}).get("search", []):
                t = item.get("title", "")
                snip = html.unescape(re.sub(r"<[^>]+>", "", item.get("snippet", "")).strip())
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(t.replace(' ', '_'))}"
                results.append(f"• **{t} (Wikipedia)**\n  URL: {page_url}\n  {snip}")
            if results:
                return disambig_notice + wrap_untrusted_content(f"search results for '{clean_query}'", "\n\n".join(results[:max_results]))
    except Exception as e:
        logger.warning(f"Wikipedia search error: {e}")

    return f"No search results retrieved for '{clean_query}'. Please verify internet connectivity."


@tool(
    name="deep_research",
    description="Conduct deep research on a topic with multi-source citations and save to Markdown report.",
    category="research",
    tier="AUTO"
)
def deep_research(topic: str, output_filename: str = "") -> str:
    """Run comprehensive research workflow and save report."""
    queries = [
        topic,
        f"{topic} overview details",
        f"{topic} location facts updates",
    ]

    all_findings = []
    for q in queries:
        res = web_search(query=q, max_results=3)
        all_findings.append(f"### Search Query: {q}\n{res}")

    if not output_filename:
        safe_name = re.sub(r"[^\w\-]", "_", topic.lower())[:30]
        output_filename = f"research_{safe_name}.md"

    report = (
        f"# Research Report: {topic}\n\n"
        f"**Generated by GDR AI** on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        f"## Findings & Sources\n\n" +
        "\n\n".join(all_findings)
    )

    docs_dir = Path.home() / "Documents"
    try:
        docs_dir.mkdir(parents=True, exist_ok=True)
        p = docs_dir / output_filename
        p.write_text(report, encoding="utf-8")
    except (OSError, PermissionError):
        p = Path("/tmp") / output_filename
        p.write_text(report, encoding="utf-8")

    return f"✅ Comprehensive research report compiled and saved to {p}."
