# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_home_ok(client):
    response = client.get(reverse("home"))
    assert response.status_code == 200
    assert b"Biddeford Eagles League" in response.content


@pytest.mark.django_db
def test_hello_fragment_ok(client):
    response = client.get(reverse("hello-fragment"))
    assert response.status_code == 200
    assert b"Hello from the server" in response.content
