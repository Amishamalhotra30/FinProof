from dataclasses import dataclass


@dataclass(frozen=True)
class CorruptionPlan:
    missing_records: int = 0
    duplicate_records: int = 0
    amount_mismatches: int = 0
    reference_mismatches: int = 0
    timing_anomalies: int = 0

    def __post_init__(self) -> None:
        values = {
            "missing_records": self.missing_records,
            "duplicate_records": self.duplicate_records,
            "amount_mismatches": self.amount_mismatches,
            "reference_mismatches": self.reference_mismatches,
            "timing_anomalies": self.timing_anomalies,
        }

        for name, value in values.items():
            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative"
                )

    @property
    def total_corruptions(self) -> int:
        return (
            self.missing_records
            + self.duplicate_records
            + self.amount_mismatches
            + self.reference_mismatches
            + self.timing_anomalies
        )