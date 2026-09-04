from dataclasses import dataclass
from enum import Enum


class SettlementStructureType(str, Enum):
    SINGLE = "SINGLE"
    SPLIT = "SPLIT"
    BUNDLED = "BUNDLED"
    MANY_TO_MANY = "MANY_TO_MANY"


@dataclass(frozen=True)
class SettlementStructure:
    """
    Describes the observed relationship structure between
    payments and settlements.

    This is structural reconstruction only.

    It does not determine whether the settlement is correct.
    """

    structure_type: SettlementStructureType

    payment_ids: tuple[str, ...]
    settlement_ids: tuple[str, ...]

    relationship_count: int


class SettlementStructureReconstructor:
    """
    Identifies the observed payment/settlement relationship shape.

    It never creates missing payments or settlements.
    """

    def reconstruct(
        self,
        payment_ids: list[str] | tuple[str, ...],
        settlement_ids: list[str] | tuple[str, ...],
        relationship_count: int,
    ) -> SettlementStructure:

        payments = tuple(payment_ids)
        settlements = tuple(settlement_ids)

        payment_count = len(payments)
        settlement_count = len(settlements)

        if (
            payment_count == 1
            and settlement_count == 1
        ):
            structure = (
                SettlementStructureType.SINGLE
            )

        elif (
            payment_count == 1
            and settlement_count > 1
        ):
            structure = (
                SettlementStructureType.SPLIT
            )

        elif (
            payment_count > 1
            and settlement_count == 1
        ):
            structure = (
                SettlementStructureType.BUNDLED
            )

        elif (
            payment_count > 1
            and settlement_count > 1
        ):
            structure = (
                SettlementStructureType.MANY_TO_MANY
            )

        else:
            structure = (
                SettlementStructureType.SINGLE
            )

        return SettlementStructure(
            structure_type=structure,
            payment_ids=payments,
            settlement_ids=settlements,
            relationship_count=relationship_count,
        )