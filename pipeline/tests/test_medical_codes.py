from medintel.medical_codes import extract_entities


def test_extracts_cpt_and_drug_terms():
    entities = extract_entities("CPT 72148 documents semaglutide evidence for obesity. PMID: 42286992.")
    values = {entity["normalized_value"] for entity in entities}
    assert "72148" in values
    assert "semaglutide" in values
    assert "42286992" in values
