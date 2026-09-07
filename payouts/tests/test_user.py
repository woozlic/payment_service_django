from decimal import Decimal

from django.contrib.auth import get_user_model

from payouts.models import Payout


def test_anonymous_denied(db):
    from rest_framework.test import APIClient
    assert APIClient().get("/api/payouts/").status_code == 401

def test_foreign_payout_invisible(api, currency):
    other = get_user_model().objects.create_user(username="mallory", password="pass12345")
    p = Payout.objects.create(user=other, currency=currency, amount=Decimal("5"), receiver_wallet="0xabcd")
    assert api.get(f"/api/payouts/{p.id}/").status_code == 404
    assert api.delete(f"/api/payouts/{p.id}/").status_code == 404