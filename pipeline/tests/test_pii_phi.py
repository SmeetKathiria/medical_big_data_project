from medintel.pii_phi import contains_phi


def test_detects_possible_phi():
    assert contains_phi("Patient: ABC123")
    assert not contains_phi("CMS policy language for CPT 72148")
