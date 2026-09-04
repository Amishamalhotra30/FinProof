from app.ingestion.quality import QualityStatus


def assess_quality(
    errors: list[str],
) -> QualityStatus:

    if not errors:
        return QualityStatus.VALID

    return QualityStatus.INVALID