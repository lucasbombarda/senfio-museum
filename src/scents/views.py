from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from scents.models import (
    Batch,
    Capsule,
    MuseumProfile,
    QualityCheck,
    Reservation,
    StatusChange,
)
from scents.permissions import IsCurator
from scents.serializers import (
    BatchSerializer,
    CapsuleSerializer,
    ExternalEventSerializer,
    MuseumProfileSerializer,
    QualityCheckSerializer,
    ReservationSerializer,
    StatusChangeSerializer,
)


class BatchViewSet(viewsets.ModelViewSet):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer


class CapsuleViewSet(viewsets.ModelViewSet):
    queryset = Capsule.objects.select_related("batch").all()
    serializer_class = CapsuleSerializer
    filterset_fields = ["status", "rarity"]


class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related("capsule", "capsule__batch").all()
    serializer_class = ReservationSerializer

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        reservation = self.get_object()
        now = timezone.now()

        # WARN: BR-002
        """
        - Ao criar uma reserva válida, a cápsula deve mudar para `reserved`.
            Ok

        - Uma reserva só pode ser retirada enquanto estiver `pending`.
            Ok

        - Se o prazo de retirada expirar, a reserva deve mudar para `expired`
        e a cápsula deve voltar para `available`.
            Ok

        - Cápsulas raras ou únicas exigem aprovação manual antes do checkout
        (a aprovação é do curador — ver BR-004).
            Falta: cápsula `rare`/`unique` (requires_manual_approval) exige
            aprovação do curador antes do checkout. Não é checado.

        - Ao devolver uma cápsula sem dano, a reserva deve mudar para
        `returned` e a cápsula para `available`.
        - Ao devolver uma cápsula com dano, a cápsula deve ir para `quarantine`
        e uma inspeção deve ser registrada.
            Falta: devolução (returned/quarantine) não existe.


        """
        if reservation.status != Reservation.Status.PENDING:
            return Response(
                {"detail": "Somente reservas pendentes podem ser retiradas."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if reservation.pickup_deadline < now:
            reservation.status = Reservation.Status.EXPIRED
            reservation.capsule.status = Capsule.Status.AVAILABLE
            reservation.save(update_fields=["status"])
            reservation.capsule.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Reserva expirada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reservation.status = Reservation.Status.CHECKED_OUT
        reservation.checked_out_at = now
        reservation.capsule.status = Capsule.Status.CHECKED_OUT
        reservation.save(update_fields=["status", "checked_out_at"])
        reservation.capsule.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(reservation).data)


class QualityCheckViewSet(viewsets.ModelViewSet):
    queryset = QualityCheck.objects.select_related("capsule", "reservation").all()
    serializer_class = QualityCheckSerializer


class MuseumProfileViewSet(viewsets.ModelViewSet):
    queryset = MuseumProfile.objects.select_related("user").all()
    serializer_class = MuseumProfileSerializer
    permission_classes = [IsCurator]


class StatusChangeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StatusChange.objects.select_related("capsule").all()
    serializer_class = StatusChangeSerializer


class ExternalMuseumWebhookView(APIView):
    def post(self, request):
        # WARN: BR-003
        """
        Evento novo registrado e processado.
            Ok

        Repetido (source + event_id) retorna sucesso sem duplicar.
            Falta: sem checagem nem unique_together. Duplica sempre.

        capsule.quarantined manda cápsula pra quarentena.
            Meio: update() silencioso, capsule_id ausente/inexistente nao erra.

        Payload invalido retorna erro claro.
            Falta: payload e JSONField livre, capsule_id nunca validado.
        """
        serializer = ExternalEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = serializer.save(processed_at=timezone.now())

        if event.event_type == "capsule.quarantined":
            capsule_id = event.payload.get("capsule_id")
            Capsule.objects.filter(id=capsule_id).update(status=Capsule.Status.QUARANTINE)

        return Response(ExternalEventSerializer(event).data, status=status.HTTP_201_CREATED)
