from decimal import Decimal
from rest_framework import serializers
from .models import Payout, Currency



class PayoutSerializer(serializers.ModelSerializer):
    currency = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Currency.objects.all(),
    )

    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2,
        min_value=Decimal('0.01'), max_value=Decimal('10000000')
    )
    receiver_wallet = serializers.CharField(min_length=4, max_length=64)

    TRANSITIONS = {
        Payout.Status.PENDING: {Payout.Status.PAID, Payout.Status.FAILED},
        Payout.Status.PAID: set(),
        Payout.Status.FAILED: {Payout.Status.PENDING}
    }
    class Meta:
        model = Payout
        fields = ['id', 'amount', 'currency', 'status', 'receiver_wallet', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

        extra_kwargs = {
            "receiver_wallet": {"required": True, "allow_blank": False},
        }

    def validate_receiver_wallet(self, value):
        value = value.strip()
        if len(value) < 4 or len(value) > 16:
            raise serializers.ValidationError("Receiver wallet should be between 4 and 16 symbols")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status != Payout.Status.PENDING:
            if set(attrs) - {"status"}:
                raise serializers.ValidationError("Only status can change after processing")
        return attrs

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


class PayoutCreateSerializer(PayoutSerializer):
    class Meta(PayoutSerializer.Meta):
        read_only_fields = PayoutSerializer.Meta.read_only_fields + ['status']
