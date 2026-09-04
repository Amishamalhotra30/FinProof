from datetime import datetime

from app.evidence.graph import EvidenceGraph
from app.reconciliation.ambiguity_resolver import (
    AmbiguityResolver,
    Resolution,
    ResolutionStatus,
)
from app.reconciliation.candidate_generator import (
    CandidateGenerator,
    RelationshipCandidate,
)
from app.reconciliation.exact_matcher import (
    ExactMatcher,
)
from app.reconciliation.graph import (
    ReconciliationGraph,
)
from app.reconciliation.models import (
    Cardinality,
    MatchMethod,
    Relationship,
    RelationshipStatus,
    RelationshipType,
)
from app.reconciliation.normalized_matcher import (
    NormalizedMatcher,
)
from app.reconciliation.scorer import (
    CandidateScorer,
    ScoredCandidate,
)


class ReconciliationResolver:
    """
    Phase 3 orchestration layer.

    Resolution order:

        1. Exact matching
        2. Normalized matching
        3. Candidate generation
        4. Candidate scoring
        5. Ambiguity resolution

    Existing deterministic relationships always take
    precedence over candidate-based relationships.
    """

    def __init__(
        self,
        ambiguity_resolver: AmbiguityResolver | None = None,
    ) -> None:

        self.exact_matcher = ExactMatcher()

        self.normalized_matcher = (
            NormalizedMatcher()
        )

        self.candidate_generator = (
            CandidateGenerator()
        )

        self.scorer = CandidateScorer()

        self.ambiguity_resolver = (
            ambiguity_resolver
            or AmbiguityResolver()
        )

    def resolve(
        self,
        evidence_graph: EvidenceGraph,
    ) -> ReconciliationGraph:
        """
        Resolve relationships in the evidence graph.

        Deterministic matches are established first.
        Only relationships that remain unresolved are
        passed through candidate scoring and ambiguity
        resolution.
        """

        # -------------------------------------------------
        # Step 1:
        # Establish relationships using exact identifiers.
        # -------------------------------------------------

        graph = self.exact_matcher.match(
            evidence_graph
        )

        # -------------------------------------------------
        # Step 2:
        # Establish relationships using normalized
        # identifiers/references.
        # -------------------------------------------------

        graph = self.normalized_matcher.match(
            evidence_graph,
            existing_graph=graph,
        )

        # -------------------------------------------------
        # Step 3:
        # Generate broader candidates for relationships
        # that could not be established deterministically.
        # -------------------------------------------------

        candidates = (
            self.candidate_generator.generate(
                evidence_graph
            )
        )

        # -------------------------------------------------
        # Step 4:
        # Remove candidates whose relationship already
        # exists in the deterministic graph.
        # -------------------------------------------------

        unresolved_candidates = [
            candidate
            for candidate in candidates
            if not self._relationship_exists(
                graph=graph,
                source_id=(
                    candidate.source_record_id
                ),
                target_id=(
                    candidate.target_record_id
                ),
            )
        ]

        # -------------------------------------------------
        # Step 5:
        # Score unresolved candidates.
        # -------------------------------------------------

        scored_candidates = [
            self.scorer.score(candidate)
            for candidate
            in unresolved_candidates
        ]

        # -------------------------------------------------
        # Step 6:
        # Group candidates by source record and
        # relationship type.
        # -------------------------------------------------

        groups = self._group_candidates(
            scored_candidates
        )

        # -------------------------------------------------
        # Step 7:
        # Resolve each candidate group independently.
        # -------------------------------------------------

        for group in groups.values():

            resolution = (
                self.ambiguity_resolver.resolve(
                    group
                )
            )

            if (
                resolution.status
                == ResolutionStatus.CONFIRMED
            ):
                self._add_resolved_relationship(
                    graph=graph,
                    resolution=resolution,
                )

        return graph

    @staticmethod
    def _group_candidates(
        candidates: list[ScoredCandidate],
    ) -> dict[
        tuple[str, str],
        list[ScoredCandidate],
    ]:
        """
        Group candidates by:

            source record
            relationship type

        This allows the ambiguity resolver to determine
        the best target for each relationship independently.
        """

        groups: dict[
            tuple[str, str],
            list[ScoredCandidate],
        ] = {}

        for candidate in candidates:

            key = (
                candidate.source_record_id,
                candidate.relationship_type,
            )

            groups.setdefault(
                key,
                [],
            ).append(candidate)

        return groups

    @staticmethod
    def _relationship_exists(
        graph: ReconciliationGraph,
        source_id: str,
        target_id: str,
    ) -> bool:
        """
        Check whether a source-target relationship
        already exists in the reconciliation graph.
        """

        return any(
            relationship.source_record_id
            == source_id
            and relationship.target_record_id
            == target_id
            for relationship
            in graph.relationships
        )

    @staticmethod
    def _add_resolved_relationship(
        graph: ReconciliationGraph,
        resolution: Resolution,
    ) -> None:
        """
        Convert a confirmed candidate resolution into
        a graph relationship.
        """

        candidate = resolution.candidate

        if candidate is None:
            return

        relationship = (
            ReconciliationResolver
            ._relationship_from_candidate(
                candidate=candidate,
                resolution=resolution,
            )
        )

        graph.add_relationship(
            relationship
        )

    @staticmethod
    def _relationship_from_candidate(
        candidate: ScoredCandidate,
        resolution: Resolution,
    ) -> Relationship:
        """
        Convert a confirmed scored candidate into a
        ReconciliationGraph relationship.
        """

        relationship_type = (
            RelationshipType[
                candidate.relationship_type
            ]
        )

        evidence = list(
            candidate.reasons
        )

        return Relationship(
            relationship_id=(
                f"REL_"
                f"{candidate.source_record_id}_"
                f"{candidate.target_record_id}"
            ),
            source_record_id=(
                candidate.source_record_id
            ),
            target_record_id=(
                candidate.target_record_id
            ),
            relationship_type=(
                relationship_type
            ),
            cardinality=(
                Cardinality.ONE_TO_ONE
            ),
            method=(
                MatchMethod.AMOUNT_TIME_MATCH
            ),
            evidence=evidence,
            status=(
                RelationshipStatus.CONFIRMED
            ),
            created_at=datetime.now(),
        )
