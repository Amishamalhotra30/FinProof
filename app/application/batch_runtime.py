from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.application.models import (
    BatchMetadata,
    BatchRuntime,
    BatchStatus,
)


class BatchRuntimeStore:
    """
    In-memory runtime registry for Phase 9.

    The store deliberately contains runtime/application state only.
    It does not contain benchmark ground truth and does not perform
    financial reasoning.
    """

    def __init__(self) -> None:
        self._batches: dict[str, BatchRuntime] = {}
        self._lock = RLock()

    def create(
        self,
        batch_id: str,
        name: str,
        scenario: str,
        seed: int,
    ) -> BatchRuntime:
        with self._lock:
            if batch_id in self._batches:
                raise ValueError(
                    f"Batch already exists: {batch_id}"
                )

            runtime = BatchRuntime(
                metadata=BatchMetadata(
                    batch_id=batch_id,
                    name=name,
                    scenario=scenario,
                    seed=seed,
                    status=BatchStatus.CREATED,
                ),
                created_at=self._now(),
            )

            self._batches[batch_id] = runtime

            return runtime

    def get(self, batch_id: str) -> BatchRuntime:
        with self._lock:
            try:
                return self._batches[batch_id]
            except KeyError:
                raise KeyError(
                    f"Batch not found: {batch_id}"
                ) from None

    def exists(self, batch_id: str) -> bool:
        with self._lock:
            return batch_id in self._batches

    def save(self, runtime: BatchRuntime) -> None:
        with self._lock:
            self._batches[
                runtime.metadata.batch_id
            ] = runtime

    def delete(self, batch_id: str) -> None:
        with self._lock:
            self._batches.pop(batch_id, None)

    def clear(self) -> None:
        with self._lock:
            self._batches.clear()

    def list_batches(self) -> list[BatchRuntime]:
        with self._lock:
            return list(self._batches.values())

    @staticmethod
    def _now() -> str:
        return datetime.now(
            timezone.utc
        ).isoformat()


store = BatchRuntimeStore()


def get_batch(batch_id: str) -> BatchRuntime:
    return store.get(batch_id)


def register_batch(
    batch_id: str,
    name: str,
    scenario: str,
    seed: int,
) -> BatchRuntime:
    return store.create(
        batch_id=batch_id,
        name=name,
        scenario=scenario,
        seed=seed,
    )


def save_batch(runtime: BatchRuntime) -> None:
    store.save(runtime)