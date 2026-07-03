"""
Tests for the manual pagination helper.
Path: utils/tests/test_pagination.py
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from accounts.tests.factories import UserFactory
from utils.pagination import paginate_or_ok

User = get_user_model()

factory = APIRequestFactory()


class _UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


def _build_request(query_params=None):
    django_request = factory.get("/", query_params or {})
    return Request(django_request)


@pytest.mark.django_db
class TestPaginateOrOkWithoutPage:
    def test_returns_all_rows_when_no_page_param(self):
        UserFactory.create_batch(3)
        request = _build_request()

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert response.data["success"] is True
        assert len(response.data["data"]) == 3

    def test_no_pagination_key_in_meta_when_no_page_param(self):
        UserFactory.create_batch(3)
        request = _build_request()

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert "pagination" not in response.data["meta"]


@pytest.mark.django_db
class TestPaginateOrOkWithPage:
    def test_first_page_returns_page_size_rows_with_has_next_true(self):
        UserFactory.create_batch(5)
        request = _build_request({"page": "1", "page_size": "2"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert len(response.data["data"]) == 2
        assert response.data["meta"]["pagination"]["has_next"] is True
        assert response.data["meta"]["pagination"]["has_previous"] is False

    def test_last_page_returns_remaining_row_with_has_previous_true(self):
        UserFactory.create_batch(5)
        request = _build_request({"page": "3", "page_size": "2"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert len(response.data["data"]) == 1
        assert response.data["meta"]["pagination"]["has_next"] is False
        assert response.data["meta"]["pagination"]["has_previous"] is True

    def test_over_fetch_is_trimmed_to_page_size(self):
        UserFactory.create_batch(6)
        request = _build_request({"page": "1", "page_size": "5"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert len(response.data["data"]) == 5


@pytest.mark.django_db
class TestPaginateOrOkInvalidParams:
    def test_invalid_page_size_falls_back_to_default(self):
        UserFactory.create_batch(3)
        request = _build_request({"page": "1", "page_size": "abc"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert response.data["meta"]["pagination"]["page_size"] == 20

    def test_page_size_above_max_is_clamped_to_max(self):
        UserFactory.create_batch(3)
        request = _build_request({"page": "1", "page_size": "9999"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert response.data["meta"]["pagination"]["page_size"] == 100

    def test_invalid_page_falls_back_to_page_one(self):
        UserFactory.create_batch(3)
        request = _build_request({"page": "not-a-number"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert response.data["meta"]["pagination"]["page"] == 1

    def test_zero_page_is_clamped_to_page_one(self):
        UserFactory.create_batch(3)
        request = _build_request({"page": "0"})

        response = paginate_or_ok(None, User.objects.order_by("id"), _UserSerializer, request)

        assert response.data["meta"]["pagination"]["page"] == 1
