from app.streaming.contracts import ErrorPayload, event_name


def test_sse_error_payload_carries_structured_details() -> None:
    payload = ErrorPayload(
        stage="preprocessing",
        code="invalid_room_count",
        message="Room counts are invalid.",
        details={"room_type": "bedroom"},
        recoverable=False,
    )

    assert event_name(payload) == "error"
    assert payload.details == {"room_type": "bedroom"}
