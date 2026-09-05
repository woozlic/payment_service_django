from rest_framework import serializers
from .models import Payout, Currency



class PayoutSerializer(serializers.ModelSerializer):
    currency = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Currency.objects.all(),
    )

    TRANSITIONS = {
        Payout.Status.PENDING: {Payout.Status.PAID, Payout.Status.FAILED},
        Payout.Status.PAID: set(),
        Payout.Status.FAILED: {Payout.Status.PENDING}
    }
    class Meta:
        model = Payout
        fields = ['id', 'amount', 'currency', 'status', 'receiver_wallet', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be positive')
        return value

    def validate_status(self, value):
        if self.instance is None:
            return value
        current = self.instance.status
        if value != current and value not in self.TRANSITIONS[current]:
            raise serializers.ValidationError(f'Cannot move from {current} to {value}')
        return value


class PayoutCreateSerializer(serializers.ModelSerializer):
    class Meta(PayoutSerializer.Meta):
        read_only_fields = PayoutSerializer.Meta.read_only_fields + ['status']
