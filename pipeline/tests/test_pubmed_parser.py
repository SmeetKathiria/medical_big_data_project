from medintel.pubmed_parser import parse_pubmed


def test_pubmed_parser_sets_pubmed_document_type():
    doc = parse_pubmed({"doc_id": "p1", "source_id": "pubmed", "title": "Abstract", "text": "PMID: 42286992"})
    assert doc.metadata["document_type"] == "PubMed abstract"
