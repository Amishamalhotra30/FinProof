from dataclasses import dataclass


@dataclass(frozen=True)
class Provenance:
    evidence_id: str
    source_type: str
    source_file: str
    source_row: int


def create_provenance(
    evidence_id: str,
    source_type: str,
    source_file: str,
    source_row: int,
) -> Provenance:
    return Provenance(
        evidence_id=evidence_id,
        source_type=source_type,
        source_file=source_file,
        source_row=source_row,
    )