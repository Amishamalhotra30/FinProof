from fastapi import FastAPI

from app.api.batches import router as batches_router
from app.api.reconciliation import router as reconciliation_router
from app.api.verification import router as verification_router
from app.api.decision import router as decision_router


app = FastAPI(
    title="FinProof",
    description="Evidence-Driven Financial Control",
    version="0.1.0",
)

app.include_router(
    batches_router
)

app.include_router(
    reconciliation_router
)

app.include_router(
    verification_router
)

app.include_router(
    decision_router
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}