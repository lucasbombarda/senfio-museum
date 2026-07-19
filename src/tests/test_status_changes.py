from scents.models import StatusChange


def _change(capsule):
    return StatusChange.objects.create(
        capsule=capsule,
        from_status="available",
        to_status="reserved",
        reason="teste",
    )


def test_list_status_changes(api_client, capsule):
    _change(capsule)

    response = api_client.get("/api/status-changes/")

    assert response.status_code == 200
    assert len(response.data) == 1


def test_status_changes_are_read_only(api_client, capsule):
    change = _change(capsule)

    assert api_client.post("/api/status-changes/", {}, format="json").status_code == 405
    assert (
        api_client.patch(
            f"/api/status-changes/{change.id}/", {"reason": "x"}, format="json"
        ).status_code
        == 405
    )
    assert api_client.delete(f"/api/status-changes/{change.id}/").status_code == 405
