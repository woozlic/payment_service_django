from django.utils import timezone
from django.db import transaction

from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Payout
from .serializers import PayoutSerializer, PayoutCreateSerializer
from .tasks import process_payout


class PayoutViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PayoutSerializer

    def get_serializer_class(self):
        return PayoutCreateSerializer if self.action == 'create' else PayoutSerializer

    def get_queryset(self):
        return Payout.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        payout = serializer.save(user=self.request.user)
        transaction.on_commit(lambda: process_payout.delay(payout.id))

    def perform_update(self, serializer):
        if serializer.instance.status != Payout.Status.PENDING:
            raise ValidationError('Only pending payouts can be edited')
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        payout = self.get_object()
        payout.is_deleted = True
        payout.deleted_at = timezone.now()
        payout.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
