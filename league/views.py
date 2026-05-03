# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "league/home.html")


def hello_fragment(request: HttpRequest) -> HttpResponse:
    return render(request, "league/_hello_fragment.html")
