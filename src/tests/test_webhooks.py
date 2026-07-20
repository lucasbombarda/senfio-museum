from scents.models import ExternalEvent


def _event_payload(capsule):
    return {
        "event_id": "evt-001",
        "source": "museu-parceiro",
        "event_type": "capsule.quarantined",
        "payload": {"capsule_id": capsule.id},
    }


def test_external_webhook_records_event(api_client, capsule):
    response = api_client.post(
        "/api/webhooks/external-museum/", _event_payload(capsule), format="json"
    )

    assert response.status_code == 201
    assert response.data["event_id"] == "evt-001"


def test_external_webhook_is_idempotent(api_client, capsule):
    url = "/api/webhooks/external-museum/"

    first = api_client.post(url, _event_payload(capsule), format="json")
    second = api_client.post(url, _event_payload(capsule), format="json")

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.data["id"] == first.data["id"]
    assert ExternalEvent.objects.filter(source="museu-parceiro", event_id="evt-001").count() == 1
