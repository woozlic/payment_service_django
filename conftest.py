import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from payouts.models import Currency


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="tester", password="pass12345")


@pytest.fixture
def api(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def currency(db):
    return Currency.objects.create(name="EUR")