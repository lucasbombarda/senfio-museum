from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import serializers

from scents.models import (
    Batch,
    Capsule,
    ExternalEvent,
    MuseumProfile,
    QualityCheck,
    Reservation,
    StatusChange,
    record_status_change,
)


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ["id", "code", "preservation_method", "produced_at", "expires_at", "notes"]


class CapsuleSerializer(serializers.ModelSerializer):
    batch_code = serializers.CharField(source="batch.code", read_only=True)

    class Meta:
        model = Capsule
        fields = [
            "id",
            "batch",
            "batch_code",
            "name",
            "scent_profile",
            "origin_story",
            "intensity",
            "rarity",
            "status",
            "expires_at",
            "requires_manual_approval",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class ReservationSerializer(serializers.ModelSerializer):
    capsule_name = serializers.CharField(source="capsule.name", read_only=True)

    class Meta:
        model = Reservation
        fields = [
            "id",
            "capsule",
            "capsule_name",
            "visitor_name",
            "starts_at",
            "pickup_deadline",
            "status",
            "checked_out_at",
            "returned_at",
            "return_notes",
            "created_at",
        ]
        read_only_fields = ["status", "checked_out_at", "returned_at", "created_at"]

    def validate(self, attrs):
        capsule = attrs.get("capsule")
        if not capsule:
            return attrs

        # WARN: BR-001
        if capsule.expires_at < timezone.localdate():
            raise serializers.ValidationError("Cápsula vencida não pode ser reservada.")

        # `available` cobre de uma vez: fora de quarentena, sem reserva ativa
        # (reserved/checked_out) e não aposentada.
        if capsule.status != Capsule.Status.AVAILABLE:
            raise serializers.ValidationError("Cápsula não está disponível para reserva.")

        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                reservation = Reservation.objects.create(**validated_data)
        except IntegrityError:
            # Constraint parcial: perdeu a corrida por outra reserva ativa.
            raise serializers.ValidationError(
                "Cápsula já possui uma reserva ativa."
            ) from None
        record_status_change(
            reservation.capsule,
            Capsule.Status.RESERVED,
            reason=f"reserva criada para {reservation.visitor_name}",
        )
        return reservation


class QualityCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityCheck
        fields = ["id", "capsule", "reservation", "inspector_name", "result", "notes", "created_at"]
        read_only_fields = ["created_at"]

    def create(self, validated_data):
        check = QualityCheck.objects.create(**validated_data)
        if check.result in {QualityCheck.Result.FAILED, QualityCheck.Result.DAMAGED}:
            check.capsule.status = Capsule.Status.QUARANTINE
            check.capsule.save(update_fields=["status", "updated_at"])
        return check


class ExternalEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalEvent
        fields = ["id", "event_id", "source", "event_type", "payload", "processed_at", "created_at"]
        read_only_fields = ["processed_at", "created_at"]


class MuseumProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MuseumProfile
        fields = ["id", "user", "role", "display_name", "created_at"]
        read_only_fields = ["created_at"]


class StatusChangeSerializer(serializers.ModelSerializer):
    capsule_name = serializers.CharField(source="capsule.name", read_only=True)

    class Meta:
        model = StatusChange
        fields = [
            "id",
            "capsule",
            "capsule_name",
            "from_status",
            "to_status",
            "actor",
            "reason",
            "created_at",
        ]
        read_only_fields = ["created_at"]
