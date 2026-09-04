from app.application.failure_simulation import (
    FailureMode,
    create_failure_simulation,
    normalize_failure_mode,
)


def test_default_failure_mode_is_none():
    simulation = create_failure_simulation(None)

    assert simulation.mode == FailureMode.NONE
    assert simulation.enabled is False


def test_failure_mode_normalization():
    simulation = create_failure_simulation(
        "ai_unavailable"
    )

    assert simulation.mode == FailureMode.AI_UNAVAILABLE
    assert simulation.enabled is True
    assert simulation.display_name == "AI Unavailable"


def test_all_supported_failure_modes():
    expected = {
        "NONE",
        "AI_UNAVAILABLE",
        "EVIDENCE_RETRIEVAL_FAILURE",
        "MALFORMED_AI_OUTPUT",
        "MISSING_ADJUSTMENT_SOURCE",
        "DUPLICATE_BANK_RECORD",
        "AMBIGUOUS_SETTLEMENT",
    }

    actual = {
        mode.value
        for mode in FailureMode
    }

    assert actual == expected


def test_failure_mode_is_strict():
    try:
        normalize_failure_mode(
            "NOT_A_REAL_FAILURE"
        )
    except ValueError as exc:
        assert "Unsupported failure mode" in str(exc)
    else:
        raise AssertionError(
            "Invalid failure mode must raise ValueError"
        )


def test_failure_descriptions_are_available():
    for mode in FailureMode:
        simulation = create_failure_simulation(mode)

        assert simulation.display_name
        assert simulation.description