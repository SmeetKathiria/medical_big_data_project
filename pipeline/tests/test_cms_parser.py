from medintel.cms_parser import parse_cms


def test_cms_parser_normalizes_source_type():
    doc = parse_cms({"doc_id": "d1", "source_id": "s1", "title": "Policy", "text": "CPT 72148", "version": "2025"})
    assert doc.source_type == "cms"
    assert doc.metadata["document_type"] == "CMS policy"
