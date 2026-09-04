from app.domain.ground_truth import GroundTruthBatch
from app.generator.source_records import generate_source_records


def generate_batch_source_records(
    batch: GroundTruthBatch,
) -> dict[str, list]:
    combined_records = {
        "orders": [],
        "payments": [],
        "refunds": [],
        "fees": [],
        "adjustments": [],
        "settlements": [],
        "bank": [],
    }

    for case in batch.cases:
        records = generate_source_records(
            case.event_graph
        )

        for record_type, record_list in records.items():
            combined_records[record_type].extend(
                record_list
            )

    return combined_records