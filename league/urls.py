# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("fragment/hello/", views.hello_fragment, name="hello-fragment"),
]
