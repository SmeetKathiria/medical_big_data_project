from medintel.fda_parser import parse_fda


def test_fda_parser_normalizes_source_type():
    doc = parse_fda({"doc_id": "d1", "source_id": "s1", "title": "Label", "text": "NDA 123456"})
    assert doc.source_type == "fda"
