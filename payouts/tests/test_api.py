from decimal import Decimal

import pytest
from payouts.models import Payout

pytestmark = pytest.mark.django_db


def test_create_payout(api, currency):
    resp = api.post("/api/payouts/", {
        "amount": "100.50",
        "currency": "EUR",
        "receiver_wallet": "0x1234567890",
    }, format="json")

    assert resp.status_code == 201
    assert resp.data["status"] == Payout.Status.PENDING
    assert resp.data["currency"] == "EUR"

    payout = Payout.objects.get(id=resp.data["id"])
    assert payout.amount == Decimal("100.50")
    assert payout.user == api.handler._force_user


def test_status_ignored_on_create(api, currency):
    resp = api.post("/api/payouts/", {
        "amount": "10.00",
        "currency": "EUR",
        "receiver_wallet": "0x1234567890",
        "status": "paid",
    }, format="json")

    assert resp.status_code == 201
    assert resp.data["status"] == Payout.Status.PENDING


def test_negative_amount_rejected(api, currency):
    resp = api.post("/api/payouts/", {
        "amount": "-100.00",
        "currency": "EUR",
        "receiver_wallet": "0x1234567890",
    }, format="json")

    assert resp.status_code == 400
    assert "amount" in resp.data


def test_celery_task_called(api, currency, mocker, django_capture_on_commit_callbacks):
    mock_delay = mocker.patch("payouts.views.process_payout.delay")

    with django_capture_on_commit_callbacks(execute=True):
        resp = api.post("/api/payouts/", {
            "amount": "50.00",
            "currency": "EUR",
            "receiver_wallet": "0x1234567890",
        }, format="json")

    assert resp.status_code == 201
    mock_delay.assert_called_once_with(resp.data["id"])