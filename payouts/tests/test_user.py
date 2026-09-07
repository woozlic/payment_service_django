from payouts.models import Payout


def test_anonymous_denied(db):
    from rest_framework.test import APIClient
    assert APIClient().get("/api/payouts/").status_code == 401

