from datetime import timedelta

from django.utils import timezone

from scents.models import Capsule, QualityCheck, Reservation


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

    response = api_client.post("/api/reservations/", _reserve_payload(capsule), format="json")

    assert response.status_code == 400


def test_reservation_rejects_second_active_reservation(api_client, capsule):
    Reservation.objects.create(
        capsule=capsule,
        visitor_name="Bruno",
        starts_at=timezone.now() + timedelta(days=1),
        pickup_deadline=timezone.now() + timedelta(days=1, hours=2),
    )

    response = api_client.post("/api/reservations/", _reserve_payload(capsule), format="json")

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


def _checked_out_reservation(capsule):
    return Reservation.objects.create(
        capsule=capsule,
        visitor_name="Bruno",
        starts_at=timezone.now() + timedelta(days=1),
        pickup_deadline=timezone.now() + timedelta(days=1, hours=2),
        status=Reservation.Status.CHECKED_OUT,
    )


def test_return_without_damage(api_client, capsule):
    reservation = _checked_out_reservation(capsule)

    response = api_client.post(f"/api/reservations/{reservation.id}/return/", format="json")

    assert response.status_code == 200
    reservation.refresh_from_db()
    capsule.refresh_from_db()
    assert reservation.status == Reservation.Status.RETURNED
    assert capsule.status == Capsule.Status.AVAILABLE


def test_return_with_damage_quarantines_and_records_inspection(api_client, capsule):
    reservation = _checked_out_reservation(capsule)

    response = api_client.post(
        f"/api/reservations/{reservation.id}/return/",
        {"damaged": True, "notes": "vidro trincado"},
        format="json",
    )

    assert response.status_code == 200
    capsule.refresh_from_db()
    assert capsule.status == Capsule.Status.QUARANTINE
    assert (
        QualityCheck.objects.filter(
            reservation=reservation, result=QualityCheck.Result.DAMAGED
        ).count()
        == 1
    )


def test_return_rejects_non_checked_out(api_client, capsule):
    reservation = Reservation.objects.create(
        capsule=capsule,
        visitor_name="Ana",
        starts_at=timezone.now() + timedelta(days=1),
        pickup_deadline=timezone.now() + timedelta(days=1, hours=2),
    )

    response = api_client.post(f"/api/reservations/{reservation.id}/return/", format="json")

    assert response.status_code == 400
