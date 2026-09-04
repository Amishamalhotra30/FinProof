from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException

from app.evidence.graph import EvidenceGraph
from app.reconciliation.service import (
    ReconciliationService,
    ReconciliationServiceResult,
)


@dataclass
class ReconciliationBatchStore:
    """
    In-memory application store for reconciliation inputs
    and results.

    This is intentionally separate from the synthetic generator
    and does not contain ground-truth data.
    """

    evidence_graphs: dict[str, EvidenceGraph] = field(
        default_factory=dict
    )

    results: dict[
        str,
        ReconciliationServiceResult,
    ] = field(
        default_factory=dict
    )

    def register(
        self,
        batch_id: str,
        evidence_graph: EvidenceGraph,
    ) -> None:

        self.evidence_graphs[batch_id] = evidence_graph

    def get_graph(
        self,
        batch_id: str,
    ) -> EvidenceGraph:

        graph = self.evidence_graphs.get(
            batch_id
        )

        if graph is None:
            raise KeyError(
                f"Batch not found: {batch_id}"
            )

        return graph

    def save_result(
        self,
        batch_id: str,
        result: ReconciliationServiceResult,
    ) -> None:

        self.results[batch_id] = result

    def get_result(
        self,
        batch_id: str,
    ) -> ReconciliationServiceResult:

        result = self.results.get(
            batch_id
        )

        if result is None:
            raise KeyError(
                f"Reconciliation not found: {batch_id}"
            )

        return result

    def clear(self) -> None:
        self.evidence_graphs.clear()
        self.results.clear()


store = ReconciliationBatchStore()

router = APIRouter(
    prefix="",
    tags=["reconciliation"],
)

service = ReconciliationService()


def _get_batch_graph(
    batch_id: str,
) -> EvidenceGraph:

    try:
        return store.get_graph(
            batch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


def _get_batch_result(
    batch_id: str,
) -> ReconciliationServiceResult:

    try:
        return store.get_result(
            batch_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


def _serialize_metrics(
    metrics,
) -> dict[str, Any]:

    return {
        "relationships_processed": (
            metrics.relationships_processed
        ),
        "confirmed_relationships": (
            metrics.confirmed_relationships
        ),
        "ambiguous_relationships": (
            metrics.ambiguous_relationships
        ),
        "unresolved_relationships": (
            metrics.unresolved_relationships
        ),
        "ai_assisted_relationships": (
            metrics.ai_assisted_relationships
        ),
        "processing_time_ms": str(
            metrics.processing_time_ms
        ),
        "relationship_precision": (
            None
            if metrics.relationship_precision is None
            else str(
                metrics.relationship_precision
            )
        ),
        "relationship_recall": (
            None
            if metrics.relationship_recall is None
            else str(
                metrics.relationship_recall
            )
        ),
        "ambiguity_rate": str(
            metrics.ambiguity_rate
        ),
        "ai_assisted_rate": str(
            metrics.ai_assisted_rate
        ),
        "throughput": str(
            metrics.throughput
        ),
    }


def _serialize_relationship(
    relationship,
) -> dict[str, Any]:

    return {
        "relationship_id": (
            relationship.relationship_id
        ),
        "source_record_id": (
            relationship.source_record_id
        ),
        "target_record_id": (
            relationship.target_record_id
        ),
        "relationship_type": (
            relationship.relationship_type.value
        ),
        "cardinality": (
            relationship.cardinality.value
        ),
        "method": (
            relationship.method.value
        ),
        "evidence": list(
            relationship.evidence
        ),
        "status": (
            relationship.status.value
        ),
        "created_at": (
            relationship.created_at.isoformat()
        ),
    }


def _serialize_review_item(
    item,
) -> dict[str, Any]:

    return {
        "review_id": item.review_id,
        "source_record_id": (
            item.source_record_id
        ),
        "candidate_record_id": (
            item.candidate_record_id
        ),
        "relationship": (
            item.relationship.value
        ),
        "supporting_evidence": list(
            item.supporting_evidence
        ),
        "contradicting_evidence": list(
            item.contradicting_evidence
        ),
        "status": item.status.value,
        "requires_review": (
            item.requires_review
        ),
        "created_at": (
            item.created_at.isoformat()
        ),
        "model_name": item.model_name,
        "model_version": item.model_version,
    }


@router.post(
    "/batches/{batch_id}/reconcile"
)
def reconcile_batch(
    batch_id: str,
) -> dict[str, Any]:

    evidence_graph = _get_batch_graph(
        batch_id
    )

    result = service.reconcile(
        evidence_graph
    )

    store.save_result(
        batch_id,
        result,
    )

    return {
        "batch_id": batch_id,
        "node_count": result.node_count,
        "relationship_count": (
            result.relationship_count
        ),
        "relationships": [
            _serialize_relationship(
                relationship
            )
            for relationship
            in result.relationships
        ],
        "review_items": [
            _serialize_review_item(
                item
            )
            for item
            in result.review_items
        ],
        "metrics": _serialize_metrics(
            result.metrics
        ),
    }


@router.get(
    "/batches/{batch_id}/reconciliation"
)
def get_reconciliation(
    batch_id: str,
) -> dict[str, Any]:

    result = _get_batch_result(
        batch_id
    )

    return {
        "batch_id": batch_id,
        "node_count": result.node_count,
        "relationship_count": (
            result.relationship_count
        ),
        "relationships": [
            _serialize_relationship(
                relationship
            )
            for relationship
            in result.relationships
        ],
        "review_items": [
            _serialize_review_item(
                item
            )
            for item
            in result.review_items
        ],
        "metrics": _serialize_metrics(
            result.metrics
        ),
    }


@router.get(
    "/relationships/{relationship_id}"
)
def get_relationship(
    relationship_id: str,
) -> dict[str, Any]:

    for result in store.results.values():

        for relationship in (
            result.graph.relationships
        ):

            if (
                relationship.relationship_id
                == relationship_id
            ):
                return _serialize_relationship(
                    relationship
                )

    raise HTTPException(
        status_code=404,
        detail=(
            "Relationship not found: "
            f"{relationship_id}"
        ),
    )


@router.get(
    "/batches/{batch_id}/reconciliation/ambiguous"
)
def get_ambiguous_relationships(
    batch_id: str,
) -> dict[str, Any]:

    result = _get_batch_result(
        batch_id
    )

    return {
        "batch_id": batch_id,
        "count": len(
            result.ambiguous_review_items
        ),
        "items": [
            _serialize_review_item(
                item
            )
            for item
            in result.ambiguous_review_items
        ],
    }