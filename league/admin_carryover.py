# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Biddeford Eagles League contributors

"""Admin mixin: pre-fill add form after *Save and add another* from query string."""

from __future__ import annotations

import datetime
from typing import Any
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext as _


class CarryoverFieldsOnAddAnotherMixin:
    """
    After *Save and add another*, redirect to the add URL with ``carryover_fields``
    as query parameters taken from the saved instance. The next GET uses them as
    form initial values (admin can still change any field).

    List concrete field names (FKs use their form field name, e.g. ``season_team``).
    Omit fields that should reset each time (e.g. ``player`` on roster entries).
    """

    carryover_fields: tuple[str, ...] = ()

    def get_changeform_initial_data(self, request: Any) -> dict[str, str]:
        initial = super().get_changeform_initial_data(request)
        if request.method != "GET" or not self.carryover_fields:
            return initial
        for name in self.carryover_fields:
            raw = request.GET.get(name)
            if raw is not None and raw != "":
                initial[name] = raw
        return initial

    def _carryover_query_dict(self, obj: Any) -> dict[str, str]:
        out: dict[str, str] = {}
        for name in self.carryover_fields:
            field = obj._meta.get_field(name)
            if field.is_relation and getattr(field, "many_to_one", False):
                pk = getattr(obj, field.attname)
                if pk is not None:
                    out[name] = str(pk)
                continue
            val = getattr(obj, field.attname)
            if val is None:
                continue
            if isinstance(val, datetime.datetime):
                out[name] = val.date().isoformat()
            elif isinstance(val, datetime.date):
                out[name] = val.isoformat()
            else:
                out[name] = str(val)
        return out

    def response_add(self, request: Any, obj: Any, post_url_continue: Any = None):
        if "_addanother" not in request.POST or not self.carryover_fields:
            return super().response_add(request, obj, post_url_continue)

        opts = obj._meta
        preserved_filters = self.get_preserved_filters(request)
        preserved_qsl = self._get_preserved_qsl(request, preserved_filters)
        obj_url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=(quote(obj.pk),),
            current_app=self.admin_site.name,
        )
        if self.has_change_permission(request, obj):
            obj_repr = format_html('<a href="{}">{}</a>', obj_url, obj)
        else:
            obj_repr = str(obj)
        msg_dict = {"name": opts.verbose_name, "obj": obj_repr}
        msg = format_html(
            _(
                "The {name} “{obj}” was added successfully. You may add another "
                "{name} below."
            ),
            **msg_dict,
        )
        self.message_user(request, msg, messages.SUCCESS)

        carry = self._carryover_query_dict(obj)
        redirect_url = request.path
        if carry:
            redirect_url = f"{request.path}?{urlencode(carry)}"
        redirect_url = add_preserved_filters(
            {
                "preserved_filters": preserved_filters,
                "preserved_qsl": preserved_qsl,
                "opts": opts,
            },
            redirect_url,
        )
        return HttpResponseRedirect(redirect_url)
