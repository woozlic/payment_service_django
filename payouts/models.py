from django.core.validators import MinValueValidator
from django.db import models
from django.conf import settings
from decimal import Decimal


class Currency(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.name

class Payout(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    id = models.BigAutoField(primary_key=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payouts",
    )
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    receiver_wallet = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment = models.TextField()
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name="amount_positive"),
        ]
