from __future__ import annotations

import argparse
import gzip
import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

from medintel.config import get_settings
from medintel.r2_storage import LocalLake


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return " ".join(part.strip() for part in node.itertext() if part and part.strip())


def _publication_date(article: ET.Element) -> str | None:
    year = article.findtext(".//JournalIssue/PubDate/Year") or article.findtext(".//PubDate/Year")
    month = article.findtext(".//JournalIssue/PubDate/Month") or article.findtext(".//PubDate/Month") or "01"
    day = article.findtext(".//JournalIssue/PubDate/Day") or article.findtext(".//PubDate/Day") or "01"
    if not year:
        return None
    month_map = {
        "jan": "01",
        "feb": "02",
        "mar": "03",
        "apr": "04",
        "may": "05",
        "jun": "06",
        "jul": "07",
        "aug": "08",
        "sep": "09",
        "oct": "10",
        "nov": "11",
        "dec": "12",
    }
    month_value = month_map.get(month[:3].lower(), month.zfill(2) if month.isdigit() else "01")
    day_value = day.zfill(2) if day.isdigit() else "01"
    return f"{year[:4]}-{month_value[:2]}-{day_value[:2]}"


def _article_to_doc(article: ET.Element, archive_name: str) -> dict[str, Any] | None:
    pmid = article.findtext(".//PMID")
    if not pmid:
        return None
    title = _text(article.find(".//ArticleTitle")) or f"PubMed article {pmid}"
    abstract = " ".join(_text(node) for node in article.findall(".//AbstractText")).strip()
    if not abstract:
        return None
    pub_date = _publication_date(article)
    mesh_terms = [_text(node) for node in article.findall(".//MeshHeading/DescriptorName")]
    return {
        "doc_id": f"pubmed-{pmid}",
        "source_id": "pubmed-baseline",
        "source_type": "pubmed",
        "title": title,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}",
        "publication_date": pub_date,
        "effective_date": pub_date,
        "version": f"PMID{pmid}",
        "text": f"{abstract} PMID: {pmid}.",
        "metadata": {
            "document_type": "PubMed baseline abstract",
            "pmid": pmid,
            "source_archive": archive_name,
            "mesh_terms": mesh_terms[:25],
        },
    }


def _iter_pubmed_docs(paths: list[Path], max_docs: int | None = None) -> Iterable[dict[str, Any]]:
    emitted = 0
    for path in paths:
        with gzip.open(path, "rb") as handle:
            for _, elem in ET.iterparse(handle, events=("end",)):
                if elem.tag != "PubmedArticle":
                    continue
                doc = _article_to_doc(elem, path.name)
                elem.clear()
                if not doc:
                    continue
                yield doc
                emitted += 1
                if max_docs is not None and emitted >= max_docs:
                    return


def _count_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as handle:
        for _ in handle:
            count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--baseline-run-id", default=None)
    parser.add_argument("--max-files", type=int, default=None)
    parser.add_argument("--max-docs", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    settings = get_settings()
    lake = LocalLake(settings)
    baseline_run_id = args.baseline_run_id or args.run_id
    manifest = lake.path("raw", "pubmed_baseline_medium", f"{baseline_run_id}_manifest.jsonl")
    paths: list[Path] = []
    with manifest.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            paths.append(Path(json.loads(line)["path"]))
    if args.max_files is not None:
        paths = paths[: args.max_files]
    if not paths:
        raise SystemExit(f"No PubMed baseline archives found in {manifest}")

    out = lake.path("raw", "pubmed", f"{args.run_id}_pubmed.jsonl")
    summary_path = lake.path("reports", "pubmed_medium", f"{args.run_id}_raw_pubmed_summary.json")
    if not args.force and out.exists() and summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        expected = int(summary.get("documents_written") or -1)
        actual = _count_lines(out)
        if expected == actual and summary.get("input_files") == len(paths):
            print(json.dumps({**summary, "reused_existing_output": True}, indent=2))
            return
        print(
            json.dumps(
                {
                    "rebuilding": str(out),
                    "reason": "summary/file mismatch",
                    "summary_documents_written": expected,
                    "actual_lines": actual,
                    "summary_input_files": summary.get("input_files"),
                    "actual_input_files": len(paths),
                },
                indent=2,
            )
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_out = out.with_suffix(out.suffix + ".tmp")
    tmp_summary = summary_path.with_suffix(summary_path.suffix + ".tmp")
    count = 0
    with tmp_out.open("w", encoding="utf-8") as handle:
        for doc in _iter_pubmed_docs(paths, args.max_docs):
            handle.write(json.dumps(doc, sort_keys=True) + "\n")
            count += 1
    summary = {
        "run_id": args.run_id,
        "baseline_run_id": baseline_run_id,
        "input_files": len(paths),
        "documents_written": count,
        "output": str(out),
    }
    tmp_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    os.replace(tmp_out, out)
    os.replace(tmp_summary, summary_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
