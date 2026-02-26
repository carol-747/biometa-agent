"""
PubMed article fetcher using Bio.Entrez (Biopython).
Retrieves all 19 metadata fields defined in the project spec.
"""
import logging
import time
from typing import Any
from Bio import Entrez, Medline
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def configure_entrez(email: str):
    Entrez.email = email
    Entrez.tool = "BiometaAgent"


def search_pubmed(query: str, max_results: int = 1000, retstart: int = 0) -> list[str]:
    """Return a list of PMIDs for a query."""
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        retstart=retstart,
        usehistory="y",
    )
    record = Entrez.read(handle)
    handle.close()
    return record.get("IdList", [])


def fetch_articles_batch(pmids: list[str], retries: int = 3) -> list[dict[str, Any]]:
    """Fetch full article records for a list of PMIDs, return list of dicts."""
    if not pmids:
        return []

    id_str = ",".join(pmids)
    for attempt in range(retries):
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=id_str,
                rettype="xml",
                retmode="xml",
            )
            xml_data = handle.read()
            handle.close()
            return _parse_pubmed_xml(xml_data)
        except Exception as e:
            logger.warning(f"Fetch attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    return []


def _parse_pubmed_xml(xml_data: bytes) -> list[dict[str, Any]]:
    """Parse PubMed XML and extract all 19 metadata fields."""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return []

    articles = []
    for article_node in root.findall(".//PubmedArticle"):
        try:
            record = _extract_article(article_node)
            if record:
                articles.append(record)
        except Exception as e:
            logger.warning(f"Error parsing article: {e}")
    return articles


def _text(node, path: str, default: str = "") -> str:
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else default


def _all_text(node, path: str) -> list[str]:
    return [el.text.strip() for el in node.findall(path) if el.text]


def _extract_article(node) -> dict[str, Any] | None:
    mc = node.find("MedlineCitation")
    if mc is None:
        return None

    article = mc.find("Article")
    if article is None:
        return None

    # 1. PMID
    pmid = _text(mc, "PMID")
    if not pmid:
        return None

    # 2. Title
    title = _text(article, "ArticleTitle")

    # 3. Abstract
    abstract_parts = article.findall(".//AbstractText")
    if abstract_parts:
        abstract = " ".join(
            (el.get("Label", "") + ": " if el.get("Label") else "") + (el.text or "")
            for el in abstract_parts
        ).strip()
    else:
        abstract = ""

    # 4. Authors
    authors = []
    for author in article.findall(".//Author"):
        last = _text(author, "LastName")
        first = _text(author, "ForeName")
        initials = _text(author, "Initials")
        collective = _text(author, "CollectiveName")
        name = collective or f"{last} {initials}".strip() or f"{last} {first}".strip()
        affil_list = [a.text for a in author.findall(".//AffiliationInfo/Affiliation") if a.text]
        authors.append({"name": name, "affiliation": affil_list[0] if affil_list else None})

    # 5. Journal
    journal = _text(article, ".//Journal/Title") or _text(article, ".//Journal/ISOAbbreviation")

    # 6. pub_date
    pub_date_node = article.find(".//Journal/JournalIssue/PubDate")
    if pub_date_node is not None:
        year = _text(pub_date_node, "Year")
        month = _text(pub_date_node, "Month")
        day = _text(pub_date_node, "Day")
        medline_date = _text(pub_date_node, "MedlineDate")
        pub_date = medline_date or " ".join(filter(None, [year, month, day]))
    else:
        pub_date = ""

    # 7. DOI
    doi = ""
    for eid in article.findall(".//ELocationID"):
        if eid.get("EIdType") == "doi":
            doi = eid.text or ""
            break

    # 8. Keywords
    keywords = _all_text(mc, ".//KeywordList/Keyword")

    # 9. MeSH terms
    mesh_terms = []
    for mh in mc.findall(".//MeshHeadingList/MeshHeading"):
        descriptor = _text(mh, "DescriptorName")
        qualifiers = _all_text(mh, "QualifierName")
        if descriptor:
            mesh_terms.append(descriptor)
            mesh_terms.extend([f"{descriptor}/{q}" for q in qualifiers])

    # 10. Publication type
    publication_type = _all_text(article, ".//PublicationTypeList/PublicationType")

    # 11. Language
    language = _text(article, ".//Language")

    # 12. Country
    country = _text(mc, ".//MedlineJournalInfo/Country")

    # 13. Affiliations (unique list from all authors)
    affil_set = set()
    for a in authors:
        if a.get("affiliation"):
            affil_set.add(a["affiliation"])
    affiliations = list(affil_set)

    # 14. Citations count (not in XML, set to None; could be fetched via elink)
    citations_count = None

    # 15. full_text_link
    full_text_link = ""
    pubmed_data = node.find("PubmedData")
    if pubmed_data is not None:
        for ref in pubmed_data.findall(".//ArticleIdList/ArticleId"):
            if ref.get("IdType") == "pmc":
                full_text_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{ref.text}/"
                break
        if not full_text_link:
            full_text_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

    # 16. grant_info
    grant_info = []
    for grant in article.findall(".//GrantList/Grant"):
        grant_info.append({
            "id": _text(grant, "GrantID"),
            "agency": _text(grant, "Agency"),
            "country": _text(grant, "Country"),
        })

    # 17. chemical_substances
    chemical_substances = []
    for chem in mc.findall(".//ChemicalList/Chemical"):
        name = _text(chem, "NameOfSubstance")
        if name:
            chemical_substances.append(name)

    # 18. references
    references = []
    if pubmed_data is not None:
        for ref in pubmed_data.findall(".//ReferenceList/Reference"):
            for aid in ref.findall(".//ArticleIdList/ArticleId"):
                if aid.get("IdType") == "pubmed" and aid.text:
                    references.append(aid.text)

    # 19. article_ids
    article_ids = {}
    if pubmed_data is not None:
        for aid in pubmed_data.findall(".//ArticleIdList/ArticleId"):
            article_ids[aid.get("IdType", "unknown")] = aid.text

    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal,
        "pub_date": pub_date,
        "doi": doi,
        "keywords": keywords,
        "mesh_terms": mesh_terms,
        "publication_type": publication_type,
        "language": language,
        "country": country,
        "affiliations": affiliations,
        "citations_count": citations_count,
        "full_text_link": full_text_link,
        "grant_info": grant_info,
        "chemical_substances": chemical_substances,
        "references": references,
        "article_ids": article_ids,
    }


def fetch_and_store(
    db_session,
    query: str,
    max_results: int = 1000,
    batch_size: int = 100,
    email: str = "researcher@example.com",
) -> int:
    """
    Full pipeline: search PubMed, fetch articles in batches, upsert to DB.
    Returns count of newly stored articles.
    """
    from app.db.models import Article
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    configure_entrez(email)
    logger.info(f"Searching PubMed: {query!r}, max={max_results}")

    pmids = search_pubmed(query, max_results=max_results)
    logger.info(f"Found {len(pmids)} PMIDs")

    stored = 0
    for i in range(0, len(pmids), batch_size):
        batch = pmids[i : i + batch_size]
        articles = fetch_articles_batch(batch)
        for art_data in articles:
            try:
                existing = db_session.query(Article).filter_by(pmid=art_data["pmid"]).first()
                if existing:
                    continue
                article = Article(**art_data)
                db_session.add(article)
                stored += 1
            except Exception as e:
                logger.warning(f"Error storing PMID {art_data.get('pmid')}: {e}")
                db_session.rollback()
        try:
            db_session.commit()
        except Exception as e:
            logger.error(f"Commit error: {e}")
            db_session.rollback()

        logger.info(f"Batch {i // batch_size + 1}: stored {stored} articles so far")
        time.sleep(0.35)  # NCBI rate limit: ~3 req/sec

    return stored
