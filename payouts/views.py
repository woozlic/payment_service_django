from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .models import Payout
from .serializers import PayoutSerializer

class PayoutViewSet(viewsets.ModelViewSet):
    serializer_class = PayoutSerializer

    def get_queryset(self):
        return Payout.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        if serializer.instance.status != Payout.Status.PENDING:
            raise ValidationError('Only pending payouts can be edited')
        serializer.save()

