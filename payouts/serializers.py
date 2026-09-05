from rest_framework import serializers
from .models import Payout, Currency


class PayoutSerializer(serializers.ModelSerializer):
    currency = serializers.SlugRelatedField(
        slug_field='name',
        queryset=Currency.objects.all(),
    )
    class Meta:
        model = Payout
        fields = ['id', 'amount', 'currency', 'status', 'receiver_wallet', 'created_at', 'updated_at']
        read_only_fields = ['status', 'created_at', 'updated_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be positive')
        return value