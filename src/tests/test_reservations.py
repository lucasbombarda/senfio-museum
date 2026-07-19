from datetime import timedelta

from django.utils import timezone

from scents.models import Capsule, Reservation


def test_reservation_rejects_expired_capsule(api_client, capsule):
    capsule.expires_at = timezone.localdate() - timedelta(days=1)
    capsule.save(update_fields=["expires_at"])

    response = api_client.post(
        "/api/reservations/",
        {
            "capsule": capsule.id,
            "visitor_name": "Ana",
            "starts_at": (timezone.now() + timedelta(days=1)).isoformat(),
            "pickup_deadline": (timezone.now() + timedelta(days=1, hours=2)).isoformat(),
        },
        format="json",
    )

    assert response.status_code == 400


def _reserve_payload(capsule):
    return {
        "capsule": capsule.id,
        "visitor_name": "Ana",
        "starts_at": (timezone.now() + timedelta(days=1)).isoformat(),
        "pickup_deadline": (timezone.now() + timedelta(days=1, hours=2)).isoformat(),
    }


def test_reservation_rejects_unavailable_capsule(api_client, capsule):
    capsule.status = Capsule.Status.QUARANTINE
    capsule.save(update_fields=["status"])

    response = api_client.post(
        "/api/reservations/", _reserve_payload(capsule), format="json"
    )

    assert response.status_code == 400


def test_reservation_rejects_second_active_reservation(api_client, capsule):
    Reservation.objects.create(
        capsule=capsule,
        visitor_name="Bruno",
        starts_at=timezone.now() + timedelta(days=1),
        pickup_deadline=timezone.now() + timedelta(days=1, hours=2),
    )

    response = api_client.post(
        "/api/reservations/", _reserve_payload(capsule), format="json"
    )

    assert response.status_code == 400
    assert Reservation.objects.filter(capsule=capsule).count() == 1


def test_checkout_marks_capsule_as_checked_out(api_client, capsule):
    reservation = Reservation.objects.create(
        capsule=capsule,
        visitor_name="Bruno",
        starts_at=timezone.now() + timedelta(days=1),
        pickup_deadline=timezone.now() + timedelta(days=1, hours=2),
    )

    response = api_client.post(f"/api/reservations/{reservation.id}/checkout/")

    assert response.status_code == 200
    capsule.refresh_from_db()
    assert capsule.status == Capsule.Status.CHECKED_OUT
