from app.ingestion.quality import QualityStatus


def test_quality_status_values():

    assert QualityStatus.VALID.value == "VALID"
    assert QualityStatus.WARNING.value == "WARNING"
    assert QualityStatus.INVALID.value == "INVALID"


def test_quality_status_is_string_enum():

    assert QualityStatus.VALID == "VALID"
    assert QualityStatus.WARNING == "WARNING"
    assert QualityStatus.INVALID == "INVALID"