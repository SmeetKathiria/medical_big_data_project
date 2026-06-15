from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

from .r2_storage import write_jsonl

CMS_MCD_DOWNLOADS = {
    "all_data": "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/all_data.zip",
    "current_lcd": "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/current_lcd.zip",
    "all_lcd": "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/all_lcd.zip",
    "current_article": "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/current_article.zip",
    "all_article": "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/all_article.zip",
    "ncd": "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/ncd.zip",
}


def _get_json(url: str, timeout: int = 20) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_text(url: str, timeout: int = 20) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _download_bytes(url: str, timeout: int = 120) -> bytes:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return response.read()


def _download_file(url: str, output: Path, timeout: int = 600) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "MedIntel local data downloader"})
    digest = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with output.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    return {
        "url": url,
        "path": str(output),
        "bytes": size,
        "sha256": digest.hexdigest(),
    }


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _nested_csv_zip(outer_zip_bytes: bytes, nested_name: str) -> zipfile.ZipFile:
    outer = zipfile.ZipFile(io.BytesIO(outer_zip_bytes))
    return zipfile.ZipFile(io.BytesIO(outer.read(nested_name)))


def _read_csv_from_zip(zf: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    csv.field_size_limit(sys.maxsize)
    with zf.open(name) as handle:
        text = io.TextIOWrapper(handle, encoding="utf-8-sig", errors="replace", newline="")
        return list(csv.DictReader(text))


def _stream_csv_from_zip(zf: zipfile.ZipFile, name: str):
    csv.field_size_limit(sys.maxsize)
    with zf.open(name) as handle:
        text = io.TextIOWrapper(handle, encoding="utf-8-sig", errors="replace", newline="")
        yield from csv.DictReader(text)


def _date(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) >= 10 and value[4] == "-":
        return value[:10]
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:8]}"
    return value[:10]


def _append_text(parts: list[str], label: str, value: str | None) -> None:
    text = _clean_html(value)
    if text:
        parts.append(f"{label}: {text}")


def _open_nested_csv_zip(outer_path: Path, nested_name: str) -> zipfile.ZipFile:
    outer = zipfile.ZipFile(outer_path)
    return zipfile.ZipFile(io.BytesIO(outer.read(nested_name)))


def _code_map(zf: zipfile.ZipFile, name: str, id_field: str, version_field: str, limit_per_doc: int = 60) -> dict[tuple[str, str], list[str]]:
    codes: dict[tuple[str, str], list[str]] = {}
    for row in _stream_csv_from_zip(zf, name):
        key = (row.get(id_field, ""), row.get(version_field, ""))
        if not key[0]:
            continue
        bucket = codes.setdefault(key, [])
        code = row.get("hcpc_code_id", "").strip()
        if code and len(bucket) < limit_per_doc:
            bucket.append(code)
    return codes


def parse_cms_mcd_current_archives(archive_dir: Path, output: Path, max_articles: int = 5000, max_lcds: int = 5000, max_ncds: int = 1000) -> int:
    article_zip = archive_dir / "current_article.zip"
    lcd_zip = archive_dir / "current_lcd.zip"
    ncd_zip = archive_dir / "ncd.zip"
    missing = [str(path) for path in [article_zip, lcd_zip, ncd_zip] if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing CMS MCD archive(s): {', '.join(missing)}")

    def rows():
        article_csv = _open_nested_csv_zip(article_zip, "current_article_csv.zip")
        article_codes = _code_map(article_csv, "article_x_hcpc_code.csv", "article_id", "article_version")
        for index, row in enumerate(_stream_csv_from_zip(article_csv, "article.csv")):
            if index >= max_articles:
                break
            article_id = row.get("article_id", "").strip()
            version = row.get("article_version", "").strip()
            display_id = row.get("display_id") or f"A{article_id}"
            parts: list[str] = []
            _append_text(parts, "Description", row.get("description"))
            _append_text(parts, "Coverage policy", row.get("cms_cov_policy"))
            _append_text(parts, "ICD-10 documentation", row.get("icd10_doc"))
            _append_text(parts, "Additional ICD-10 information", row.get("add_icd10_info"))
            _append_text(parts, "Revenue guidance", row.get("revenue_para"))
            _append_text(parts, "Comments", row.get("other_comments"))
            _append_text(parts, "Keywords", row.get("keywords"))
            text = " ".join(parts)
            if not article_id or not text:
                continue
            codes = article_codes.get((article_id, version), [])
            yield {
                "doc_id": f"cms-article-{article_id}-v{version}",
                "source_id": "cms-mcd-current-article",
                "source_type": "cms",
                "title": row.get("title") or f"CMS article {display_id}",
                "url": f"https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId={article_id}",
                "publication_date": _date(row.get("article_pub_date")),
                "effective_date": _date(row.get("article_eff_date")),
                "version": version,
                "text": text,
                "metadata": {
                    "document_type": "CMS MCD article",
                    "display_id": display_id,
                    "status": row.get("status"),
                    "codes": codes,
                    "source_archive": str(article_zip),
                },
            }

        lcd_csv = _open_nested_csv_zip(lcd_zip, "current_lcd_csv.zip")
        lcd_codes = _code_map(lcd_csv, "lcd_x_hcpc_code.csv", "lcd_id", "lcd_version")
        for index, row in enumerate(_stream_csv_from_zip(lcd_csv, "lcd.csv")):
            if index >= max_lcds:
                break
            lcd_id = row.get("lcd_id", "").strip()
            version = row.get("lcd_version", "").strip()
            determination = row.get("determination_number") or f"L{lcd_id}"
            parts = []
            _append_text(parts, "Coverage indications", row.get("indication"))
            _append_text(parts, "Diagnoses that support medical necessity", row.get("diagnoses_support"))
            _append_text(parts, "Diagnoses that do not support medical necessity", row.get("diagnoses_dont_support"))
            _append_text(parts, "Coding guidelines", row.get("coding_guidelines"))
            _append_text(parts, "Documentation requirements", row.get("doc_reqs"))
            _append_text(parts, "Coverage policy", row.get("cms_cov_policy"))
            _append_text(parts, "Associated information", row.get("associated_info"))
            _append_text(parts, "Summary of evidence", row.get("summary_of_evidence"))
            _append_text(parts, "Analysis of evidence", row.get("analysis_of_evidence"))
            _append_text(parts, "Bibliography", row.get("bibliography"))
            _append_text(parts, "Keywords", row.get("keywords"))
            text = " ".join(parts)
            if not lcd_id or not text:
                continue
            codes = lcd_codes.get((lcd_id, version), [])
            yield {
                "doc_id": f"cms-lcd-{lcd_id}-v{version}",
                "source_id": "cms-mcd-current-lcd",
                "source_type": "cms",
                "title": row.get("title") or f"CMS LCD {determination}",
                "url": f"https://www.cms.gov/medicare-coverage-database/view/lcd.aspx?lcdId={lcd_id}",
                "publication_date": _date(row.get("mcd_publish_date")),
                "effective_date": _date(row.get("rev_eff_date") or row.get("orig_det_eff_date")),
                "version": version,
                "text": text,
                "metadata": {
                    "document_type": "CMS LCD",
                    "determination_number": determination,
                    "status": row.get("status"),
                    "codes": codes,
                    "source_archive": str(lcd_zip),
                },
            }

        ncd_csv = _open_nested_csv_zip(ncd_zip, "ncd_csv.zip")
        for index, row in enumerate(_stream_csv_from_zip(ncd_csv, "ncd_trkg.csv")):
            if index >= max_ncds:
                break
            ncd_id = row.get("NCD_id", "").strip()
            version = row.get("NCD_vrsn_num", "").strip()
            section = row.get("NCD_mnl_sect") or ncd_id
            parts = []
            _append_text(parts, "Item or service", row.get("itm_srvc_desc"))
            _append_text(parts, "Indications and limitations", row.get("indctn_lmtn"))
            _append_text(parts, "Cross references", row.get("xref_txt"))
            _append_text(parts, "Other text", row.get("othr_txt"))
            _append_text(parts, "Revision history", row.get("rev_hstry"))
            _append_text(parts, "Keywords", row.get("ncd_keyword"))
            text = " ".join(parts)
            if not ncd_id or not text:
                continue
            yield {
                "doc_id": f"cms-ncd-{ncd_id}-v{version}",
                "source_id": "cms-mcd-ncd",
                "source_type": "cms",
                "title": row.get("NCD_mnl_sect_title") or f"CMS NCD {section}",
                "url": f"https://www.cms.gov/medicare-coverage-database/view/ncd.aspx?ncdid={ncd_id}",
                "publication_date": _date(row.get("trnsmtl_issnc_dt")),
                "effective_date": _date(row.get("NCD_efctv_dt")),
                "version": version,
                "text": text,
                "metadata": {
                    "document_type": "CMS NCD",
                    "manual_section": section,
                    "coverage_level": row.get("cvrg_lvl_cd"),
                    "transmittal_url": row.get("trnsmtl_url"),
                    "source_archive": str(ncd_zip),
                },
            }

    return write_jsonl(output, rows())


def fetch_cms_mcd_articles(output: Path, code: str = "72148", limit: int = 5) -> int:
    url = "https://downloads.cms.gov/medicare-coverage-database/downloads/exports/current_article.zip"
    zf = _nested_csv_zip(_download_bytes(url), "current_article_csv.zip")
    code_rows = [
        row
        for row in _read_csv_from_zip(zf, "article_x_hcpc_code.csv")
        if row.get("hcpc_code_id") == code
    ][:limit]
    wanted = {(row["article_id"], row["article_version"]) for row in code_rows}
    descriptions = {
        (row["article_id"], row["article_version"]): row
        for row in code_rows
    }
    rows = []
    for row in _read_csv_from_zip(zf, "article.csv"):
        key = (row.get("article_id", ""), row.get("article_version", ""))
        if key not in wanted:
            continue
        code_row = descriptions[key]
        article_id = row.get("article_id", "")
        version = row.get("article_version", "")
        display_id = row.get("display_id") or f"A{article_id}"
        text = _clean_html(" ".join([
            row.get("description", ""),
            row.get("other_comments", ""),
            row.get("icd10_doc", ""),
            row.get("add_icd10_info", ""),
            row.get("cms_cov_policy", ""),
        ]))
        rows.append({
            "doc_id": f"cms-article-{article_id}-v{version}",
            "source_id": "cms-mcd-current-article",
            "source_type": "cms",
            "title": row.get("title") or f"CMS article {display_id}",
            "url": f"https://www.cms.gov/medicare-coverage-database/view/article.aspx?articleId={article_id}",
            "publication_date": (row.get("article_pub_date") or "")[:10] or None,
            "effective_date": (row.get("article_eff_date") or "")[:10] or None,
            "version": version,
            "text": text,
            "metadata": {
                "document_type": "CMS MCD article",
                "display_id": display_id,
                "codes": [code],
                "code_description": code_row.get("long_description"),
                "source_zip": url,
            },
        })
    return write_jsonl(output, rows)


def download_cms_mcd_archives(output_dir: Path, datasets: list[str], force: bool = False) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for dataset in datasets:
        if dataset not in CMS_MCD_DOWNLOADS:
            allowed = ", ".join(sorted(CMS_MCD_DOWNLOADS))
            raise ValueError(f"Unknown CMS MCD dataset '{dataset}'. Allowed: {allowed}")
        url = CMS_MCD_DOWNLOADS[dataset]
        output = output_dir / f"{dataset}.zip"
        if output.exists() and not force:
            digest = hashlib.sha256()
            size = 0
            with output.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    size += len(chunk)
            record = {"url": url, "path": str(output), "bytes": size, "sha256": digest.hexdigest(), "reused": True}
        else:
            record = _download_file(url, output)
            record["reused"] = False
        record["dataset"] = dataset
        records.append(record)
    return records


def fetch_fda_labels(output: Path, limit: int = 3) -> int:
    query = urllib.parse.quote('openfda.generic_name:"semaglutide" OR description:"semaglutide"')
    url = f"https://api.fda.gov/drug/label.json?search={query}&limit={limit}"
    payload = _get_json(url)
    rows = []
    for index, item in enumerate(payload.get("results", []), start=1):
        openfda = item.get("openfda", {})
        title = ", ".join(openfda.get("brand_name") or openfda.get("generic_name") or ["FDA drug label"])
        text_parts = []
        for key in ["indications_and_usage", "warnings", "boxed_warning", "adverse_reactions"]:
            values = item.get(key) or []
            text_parts.extend(values[:2])
        app_no = (openfda.get("application_number") or [f"FDA-SEMA-{index}"])[0]
        rows.append({
            "doc_id": f"fda-label-{app_no.lower()}",
            "source_id": "openfda-drug-label",
            "source_type": "fda",
            "title": title,
            "url": "https://api.fda.gov/drug/label.json",
            "publication_date": None,
            "effective_date": item.get("effective_time", "")[:8] or None,
            "version": item.get("set_id") or app_no,
            "text": " ".join(text_parts)[:6000],
            "metadata": {
                "document_type": "FDA label",
                "application_number": app_no,
                "drug_names": openfda.get("generic_name", []) + openfda.get("brand_name", []),
                "source_api": url,
            },
        })
    return write_jsonl(output, rows)


FDA_REPRESENTATIVE_QUERIES = [
    'openfda.pharm_class_epc:"Glucagon-Like Peptide-1 Receptor Agonist"',
    'openfda.pharm_class_epc:"Sodium-Glucose Cotransporter 2 Inhibitor"',
    'openfda.pharm_class_epc:"Dipeptidyl Peptidase 4 Inhibitor"',
    'openfda.pharm_class_epc:"HMG-CoA Reductase Inhibitor"',
    'openfda.pharm_class_epc:"Angiotensin 2 Receptor Blocker"',
    'openfda.pharm_class_epc:"Direct Factor Xa Inhibitor"',
    'openfda.pharm_class_epc:"Programmed Death Receptor-1 Blocking Antibody"',
    'boxed_warning:"thyroid C-cell tumors"',
    'boxed_warning:"suicidal thoughts"',
    'warnings:"pancreatitis"',
    'warnings:"acute kidney injury"',
    'warnings:"QT prolongation"',
    'warnings:"hepatotoxicity"',
    'warnings:"embryo-fetal toxicity"',
    'indications_and_usage:"type 2 diabetes"',
    'indications_and_usage:"heart failure"',
    'indications_and_usage:"chronic kidney disease"',
    'indications_and_usage:"non-small cell lung cancer"',
    'indications_and_usage:"multiple sclerosis"',
    'openfda.generic_name:"semaglutide"',
    'openfda.generic_name:"tirzepatide"',
]


def _fda_text(item: dict[str, Any], max_chars: int) -> str:
    text_parts = []
    for key in [
        "indications_and_usage",
        "contraindications",
        "boxed_warning",
        "warnings",
        "warnings_and_cautions",
        "adverse_reactions",
        "drug_interactions",
        "dosage_and_administration",
        "clinical_studies",
        "recent_major_changes",
    ]:
        values = item.get(key) or []
        for value in values[:3]:
            clean = _clean_html(value)
            if clean:
                text_parts.append(f"{key.replace('_', ' ').title()}: {clean}")
    return " ".join(text_parts)[:max_chars]


def _fda_row(item: dict[str, Any], index: int, source_api: str, max_text_chars: int) -> dict[str, Any]:
    openfda = item.get("openfda", {})
    app_no = (openfda.get("application_number") or [f"FDA-LABEL-{index}"])[0]
    set_id = item.get("set_id") or app_no
    brand_names = openfda.get("brand_name") or []
    generic_names = openfda.get("generic_name") or []
    substance_names = openfda.get("substance_name") or []
    title = ", ".join(brand_names or generic_names or substance_names or ["FDA drug label"])
    return {
        "doc_id": f"fda-label-{str(app_no).lower()}-{str(set_id)[:8].lower()}",
        "source_id": "openfda-drug-label",
        "source_type": "fda",
        "title": title,
        "url": "https://api.fda.gov/drug/label.json",
        "publication_date": None,
        "effective_date": _date(item.get("effective_time")),
        "version": set_id,
        "text": _fda_text(item, max_text_chars),
        "metadata": {
            "document_type": "FDA label",
            "application_number": app_no,
            "set_id": set_id,
            "drug_names": generic_names + brand_names + substance_names,
            "manufacturer_names": openfda.get("manufacturer_name", []),
            "pharm_classes": openfda.get("pharm_class_epc", []) + openfda.get("pharm_class_cs", []),
            "route": openfda.get("route", []),
            "product_type": openfda.get("product_type", []),
            "source_api": source_api,
        },
    }


def fetch_fda_representative_labels(output: Path, per_query_limit: int = 25, total_limit: int = 500, max_text_chars: int = 12000) -> int:
    rows_by_key: dict[str, dict[str, Any]] = {}
    for query in FDA_REPRESENTATIVE_QUERIES:
        if len(rows_by_key) >= total_limit:
            break
        limit = max(1, min(per_query_limit, total_limit - len(rows_by_key), 100))
        url = "https://api.fda.gov/drug/label.json?" + urllib.parse.urlencode({
            "search": query,
            "limit": limit,
        })
        try:
            payload = _get_json(url, timeout=45)
        except Exception as exc:
            print({"query": query, "status": "skipped", "error": str(exc)})
            continue
        for item in payload.get("results", []):
            row = _fda_row(item, len(rows_by_key) + 1, url, max_text_chars)
            if not row["text"]:
                continue
            dedupe_key = f"{row['metadata'].get('application_number')}:{row['version']}"
            rows_by_key.setdefault(dedupe_key, row)
            if len(rows_by_key) >= total_limit:
                break
    return write_jsonl(output, rows_by_key.values())


def fetch_pubmed_abstracts(output: Path, limit: int = 5) -> int:
    term = urllib.parse.quote("semaglutide obesity GLP-1")
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={term}&retmode=json&retmax={limit}"
    ids = _get_json(search_url).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return write_jsonl(output, [])
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
    })
    root = ET.fromstring(_get_text(fetch_url))
    rows = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID") or "unknown"
        title = "".join(article.findtext(".//ArticleTitle") or "PubMed abstract")
        abstract_parts = [node.text or "" for node in article.findall(".//AbstractText")]
        year = article.findtext(".//PubDate/Year")
        pub_date = f"{year}-01-01" if year else None
        rows.append({
            "doc_id": f"pubmed-{pmid}",
            "source_id": "pubmed",
            "source_type": "pubmed",
            "title": title,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
            "publication_date": pub_date,
            "effective_date": pub_date,
            "version": f"PMID{pmid}",
            "text": " ".join(abstract_parts) + f" PMID: {pmid}.",
            "metadata": {
                "document_type": "PubMed abstract",
                "pmid": pmid,
                "condition_names": ["obesity"],
                "drug_names": ["semaglutide", "GLP-1"],
                "source_api": fetch_url,
            },
        })
    return write_jsonl(output, rows)
