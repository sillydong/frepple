#
# Copyright (C) 2007-2013 by frePPLe bv
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero
# General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from datetime import datetime
import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import FieldDoesNotExist
from django.db import connections
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.db.models.fields import CharField
from django.http import HttpResponse, Http404
from django.http.response import StreamingHttpResponse, HttpResponseServerError
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ungettext
from django.utils.encoding import force_text
from django.utils.text import format_lazy
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

from freppledb.common.models import Parameter
from freppledb.common.report import (
    GridReport,
    GridFieldText,
    GridFieldNumber,
    GridFieldDuration,
    getCurrentDate,
)
from freppledb.input.models import (
    Resource,
    Operation,
    Location,
    Buffer,
    Demand,
    Item,
    OperationPlan,
    OperationPlanMaterial,
    OperationPlanResource,
)
from freppledb.admin import data_site

import logging

logger = logging.getLogger(__name__)


@staff_member_required
def search(request):
    term = request.GET.get("term").strip()
    result = []

    # Loop over all models in the data_site
    # We are interested in models satisfying these criteria:
    #  - primary key is of type text
    #  - user has change permissions
    for cls, admn in data_site._registry.items():
        if request.user.has_perm(
            "%s.view_%s" % (cls._meta.app_label, cls._meta.object_name.lower())
        ) and isinstance(cls._meta.pk, CharField):
            descriptionExists = True
            try:
                cls._meta.get_field("description")
                query = (
                    cls.objects.using(request.database)
                    .filter(Q(pk__icontains=term) | Q(description__icontains=term))
                    .order_by("pk")
                    .values_list("pk", "description")
                )
            except FieldDoesNotExist:
                descriptionExists = False
                query = (
                    cls.objects.using(request.database)
                    .filter(pk__icontains=term)
                    .order_by("pk")
                    .values_list("pk")
                )
            count = len(query)
            if count > 0:
                result.append(
                    {
                        "value": None,
                        "label": (
                            ungettext(
                                "%(name)s - %(count)d match",
                                "%(name)s - %(count)d matches",
                                count,
                            )
                            % {
                                "name": force_text(cls._meta.verbose_name),
                                "count": count,
                            }
                        ).capitalize(),
                    }
                )
                result.extend(
                    [
                        {
                            "url": (
                                "/data/%s/%s/?noautofilter&parentreference="
                                if issubclass(cls, OperationPlan)
                                else "/detail/%s/%s/"
                            )
                            % (cls._meta.app_label, cls._meta.object_name.lower()),
                            "removeTrailingSlash": True
                            if issubclass(cls, OperationPlan)
                            else False,
                            "value": i[0],
                            "display": "%s%s"
                            % (
                                i[0],
                                " %s" % (i[1],) if descriptionExists and i[1] else "",
                            ),
                        }
                        for i in query[:10]
                    ]
                )
    # Construct reply
    return HttpResponse(
        content_type="application/json; charset=%s" % settings.DEFAULT_CHARSET,
        content=json.dumps(result).encode(settings.DEFAULT_CHARSET),
    )


class OperationPlanMixin(GridReport):
    @classmethod
    def operationplanExtraBasequery(cls, query, request):

        # special keyword superop used for search field of operationplan
        if "parentreference" in request.GET:
            parentreference = request.GET["parentreference"]
            query = query.filter(
                Q(reference=parentreference) | Q(owner__reference=parentreference)
            )

        if "freppledb.forecast" in settings.INSTALLED_APPS:
            return query.annotate(
                demands=RawSQL(
                    """
          select json_agg(json_build_array(value, key, tp))
          from (
            select
              key, value,
              case when demand.name is not null then 'D' when forecast.name is not null then 'F' end as tp
            from jsonb_each_text(operationplan.plan->'pegging')
            left outer join demand on key = demand.name
            left outer join forecast on substring(key from 0 for length(key)
                                                                 - position(' - ' in reverse(key))
                                                                 -1) = forecast.name
            where demand.name is not null or forecast.name is not null
            order by value desc, key desc
            limit 10
          ) peg""",
                    [],
                ),
                end_items=RawSQL(
                    """
          select json_agg(json_build_array(key, val))
          from (
            select coalesce(demand.item_id, forecast.item_id) as key, sum(value::numeric) as val
            from jsonb_each_text(operationplan.plan->'pegging')
            left outer join demand on key = demand.name
            left outer join forecast on substring(key from 0 for position(' - ' in key)) = forecast.name
            group by coalesce(demand.item_id, forecast.item_id)
            order by 2 desc
            limit 10
            ) peg_items""",
                    [],
                ),
            )
        else:
            return query.annotate(
                demands=RawSQL(
                    """
          select json_agg(json_build_array(value, key))
          from (
            select key, value
            from jsonb_each_text(operationplan.plan->'pegging')
            order by value desc, key desc
            limit 10
            ) peg""",
                    [],
                ),
                end_items=RawSQL(
                    """
          select json_agg(json_build_array(key, val))
          from (
            select demand.item_id as key, sum(value::numeric) as val
            from jsonb_each_text(operationplan.plan->'pegging')
            inner join demand on key = demand.name
            group by demand.item_id
            order by 2 desc
            limit 10
            ) peg_items""",
                    [],
                ),
            )

    @classmethod
    def _generate_kanban_data(cls, request, *args, **kwargs):
        # Preparation of the correct filter for a column is currently done on the client side.
        # The kanban query also doesn't know about pages.
        request.GET = request.GET.copy()
        request.GET["page"] = None
        request.limit = request.pagesize
        return cls._generate_json_data(request, *args, **kwargs)

    @classmethod
    def _generate_calendar_data(cls, request, *args, **kwargs):
        request.GET = request.GET.copy()
        request.GET["page"] = None
        request.limit = request.pagesize
        return cls._generate_json_data(request, *args, **kwargs)

    calendarmode = "duration"


class PathReport(GridReport):
    """
    A report showing the upstream supply path or following downstream a
    where-used path.
    The supply path report shows all the materials, operations and resources
    used to make a certain item.
    The where-used report shows all the materials and operations that use
    a specific item.
    """

    template = "input/path.html"
    title = _("supply path")
    filterable = False
    frozenColumns = 0
    editable = False
    default_sort = None
    isTreeView = True
    multiselect = False
    help_url = "user-interface/plan-analysis/supply-path-where-used.html"

    rows = (
        GridFieldText("depth", title=_("depth"), editable=False, sortable=False),
        GridFieldText(
            "operation",
            title=_("operation"),
            editable=False,
            sortable=False,
            formatter="detail",
            extra='"role":"input/operation"',
        ),
        GridFieldText(
            "item",
            title=_("item"),
            editable=False,
            sortable=False,
            formatter="detail",
            extra='"role":"input/item"',
        ),
        GridFieldText(
            "description",
            title=format_lazy("{} - {}", _("item"), _("description")),
            editable=False,
            sortable=False,
        ),
        GridFieldNumber(
            "priority", title=_("priority"), editable=False, sortable=False
        ),
        GridFieldNumber(
            "sizeminimum",
            title=_("size minimum"),
            editable=False,
            sortable=False,
            initially_hidden=True,
        ),
        GridFieldNumber(
            "sizemultiple",
            title=_("size multiple"),
            editable=False,
            sortable=False,
            initially_hidden=True,
        ),
        GridFieldNumber(
            "sizemaximum",
            title=_("size maximum"),
            editable=False,
            sortable=False,
            initially_hidden=True,
        ),
        GridFieldNumber(
            "quantity", title=_("quantity"), editable=False, sortable=False
        ),
        GridFieldText(
            "location",
            title=_("location"),
            field_name="location",
            formatter="detail",
            extra='"role":"input/location"',
        ),
        GridFieldText("type", title=_("type"), editable=False, sortable=False),
        GridFieldDuration(
            "duration", title=_("duration"), editable=False, sortable=False
        ),
        GridFieldDuration(
            "duration_per", title=_("duration per unit"), editable=False, sortable=False
        ),
        GridFieldText(
            "resources", editable=False, sortable=False, extra="formatter:reslistfmt"
        ),
        GridFieldText("buffers", editable=False, sortable=False, hidden=True),
        GridFieldText("suboperation", editable=False, sortable=False, hidden=True),
        GridFieldText("numsuboperations", editable=False, sortable=False, hidden=True),
        GridFieldText("parentoper", editable=False, sortable=False, hidden=True),
        GridFieldText("realdepth", editable=False, sortable=False, hidden=True),
        GridFieldText("id", editable=False, sortable=False, hidden=True),
        GridFieldText("parent", editable=False, sortable=False, hidden=True),
        GridFieldText("leaf", editable=False, sortable=False, hidden=True),
        GridFieldText("expanded", editable=False, sortable=False, hidden=True),
        GridFieldText("alternate", editable=False, sortable=False, hidden=True),
    )

    # Attributes to be specified by the subclasses
    objecttype = None
    downstream = None

    @classmethod
    def basequeryset(reportclass, request, *args, **kwargs):
        if str(reportclass.objecttype._meta) != "input.buffer":
            return reportclass.objecttype.objects.filter(name__exact=args[0]).values(
                "name"
            )
        else:
            return (
                reportclass.objecttype.objects.annotate(
                    name=RawSQL("item_id||' @ '||location_id", ())
                )
                .filter(name__exact=args[0])
                .values("name")
            )

    @classmethod
    def extra_context(reportclass, request, *args, **kwargs):
        if reportclass.downstream:
            request.session["lasttab"] = "whereused"
        else:
            request.session["lasttab"] = "supplypath"

        if reportclass.objecttype._meta.model_name == "buffer":
            index = args[0].find(" @ ")
            if index == -1:
                b = Buffer.objects.get(id=args[0])
                buffer_name = b.item.name + " @ " + b.location.name
            else:
                buffer_name = args[0]

        return {
            "title": force_text(reportclass.objecttype._meta.verbose_name)
            + " "
            + (buffer_name if "buffer_name" in vars() else args[0]),
            "post_title": _("where used")
            if reportclass.downstream
            else _("supply path"),
            "downstream": reportclass.downstream,
            "active_tab": reportclass.downstream and "whereused" or "supplypath",
            "model": reportclass.objecttype,
        }

    @classmethod
    def getOperationFromItem(reportclass, request, item_name, downstream, depth):
        cursor = connections[request.database].cursor()
        query = """
      -- MANUFACTURING OPERATIONS
      select distinct
      case when parentoperation is null then operation else sibling end,
      case when parentoperation is null then operation_location else sibling_location end,
      case when parentoperation is null then operation_type else sibling_type end,
      case when parentoperation is null then operation_priority else sibling_priority end,
      case when parentoperation is null then operation_om else sibling_om end,
      case when parentoperation is null then operation_or else sibling_or end,
      case when parentoperation is null then operation_duration else sibling_duration end,
      case when parentoperation is null then operation_duration_per else sibling_duration_per end,
      parentoperation,
      parentoperation_type,
      parentoperation_priority,
      grandparentoperation,
      grandparentoperation_type,
      grandparentoperation_priority,
      sizes,
      grandparentitem_name,
      parentitem_name,
      item_name,
      grandparentitem_description,
      parentitem_description,
      item_description
       from
      (
      select operation.name as operation,
           operation.type operation_type,
           operation.location_id operation_location,
           operation.priority as operation_priority,
           operation.duration as operation_duration,
           operation.duration_per as operation_duration_per,
           case when operation.item_id is not null then jsonb_build_object(operation.item_id||' @ '||operation.location_id, 1) else '{}'::jsonb end
           ||jsonb_object_agg(operationmaterial.item_id||' @ '||operation.location_id,
                              coalesce(operationmaterial.quantity, operationmaterial.quantity_fixed,0)) filter (where operationmaterial.id is not null) as operation_om,
           jsonb_object_agg(operationresource.resource_id, operationresource.quantity) filter (where operationresource.id is not null) as operation_or,
             parentoperation.name as parentoperation,
           parentoperation.type as parentoperation_type,
           parentoperation.priority parentoperation_priority,
             sibling.name as sibling,
           sibling.type as sibling_type,
           sibling.location_id as sibling_location,
           sibling.priority as sibling_priority,
           sibling.duration as sibling_duration,
           sibling.duration_per as sibling_duration_per,
           case when grandparentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(grandparentoperation.item_id||' @ '||grandparentoperation.location_id, 1) else '{}'::jsonb end
           ||case when parentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(parentoperation.item_id||' @ '||parentoperation.location_id, 1) else '{}'::jsonb end
           ||case when sibling.item_id is not null then jsonb_build_object(sibling.item_id||' @ '||sibling.location_id, 1) else '{}'::jsonb end
           ||coalesce(jsonb_object_agg(siblingoperationmaterial.item_id||' @ '||sibling.location_id,
                                       coalesce(siblingoperationmaterial.quantity, siblingoperationmaterial.quantity_fixed,0)) filter (where siblingoperationmaterial.id is not null), '{}'::jsonb) as sibling_om,
           jsonb_object_agg(siblingoperationresource.resource_id, siblingoperationresource.quantity)filter (where siblingoperationresource.id is not null) as sibling_or,
             grandparentoperation.name as grandparentoperation,
           grandparentoperation.type as grandparentoperation_type,
           grandparentoperation.priority as grandparentoperation_priority,
           jsonb_build_object( 'operation_min', operation.sizeminimum,
                               'operation_multiple', operation.sizemultiple,
                               'operation_max', operation.sizemaximum,
                               'parentoperation_min', parentoperation.sizeminimum,
                               'parentoperation_multiple',parentoperation.sizemultiple,
                               'parentoperation_max', parentoperation.sizemaximum,
                               'grandparentoperation_min', grandparentoperation.sizeminimum,
                               'grandparentoperation_multiple', grandparentoperation.sizemultiple,
                               'grandparentoperation_max', grandparentoperation.sizemaximum) as sizes,
           grandparentitem.name as grandparentitem_name,
           parentitem.name as parentitem_name,
           item.name as item_name,
           grandparentitem.description as grandparentitem_description,
           parentitem.description as parentitem_description,
           item.description as item_description
      from operation
      left outer join operationmaterial on operationmaterial.operation_id = operation.name
      left outer join operationresource on operationresource.operation_id = operation.name
      left outer join operation parentoperation on parentoperation.name = operation.owner_id
      left outer join operation grandparentoperation on grandparentoperation.name = parentoperation.owner_id
      left outer join operation sibling on sibling.owner_id = parentoperation.name
      left outer join operationmaterial siblingoperationmaterial on siblingoperationmaterial.operation_id = sibling.name
      left outer join operationresource siblingoperationresource on siblingoperationresource.operation_id = sibling.name
      left outer join item grandparentitem on grandparentitem.name = grandparentoperation.item_id
      left outer join item parentitem on parentitem.name = parentoperation.item_id
      left outer join item on item.name = coalesce(operation.item_id,
                                                   (select item_id from operationmaterial where operation_id = operation.name and quantity > 0 limit 1))
      where operation.type in ('time_per','fixed_time')
      %s
      group by operation.name, parentoperation.name, sibling.name, grandparentoperation.name,
      grandparentitem.name, parentitem.name, item.name, grandparentitem.description, parentitem.description, item.description
      ) t
      union all
      -- DISTRIBUTION OPERATIONS
      select 'Ship '||item.name||' from '||itemdistribution.origin_id||' to '||itemdistribution.location_id,
      itemdistribution.location_id,
      'distribution' as type,
      priority,
      jsonb_build_object(item.name||' @ '||itemdistribution.origin_id, -1,
                         item.name||' @ '||itemdistribution.location_id, 1) as operation_om,
      case when itemdistribution.resource_id is not null
      then jsonb_build_object(itemdistribution.resource_id, itemdistribution.resource_qty)
      else '{}'::jsonb end operation_or,
      leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemdistribution.sizeminimum,
                               'operation_multiple', itemdistribution.sizemultiple,
                               'operation_max', itemdistribution.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemdistribution
      inner join item parent on parent.name = itemdistribution.item_id
      inner join item on item.name = %%s and item.lft between parent.lft and parent.rght
      """ % (
            (
                """
                and (operation.item_id = %s or
                (exists (select 1 from operationmaterial op1 where op1.operation_id = operation.name and op1.item_id = %s and op1.quantity > 0))
                or parentoperation.item_id = %s
                or grandparentoperation.item_id = %s)
            """,
            )
            if not downstream
            else (
                """
                and exists (select 1 from operationmaterial om where om.operation_id = operation.name
                and om.item_id = %s and om.quantity < 0)
            """,
            )
        )

        if not downstream:
            query = (
                query
                + """
        union all
      -- PURCHASING OPERATIONS
      select 'Purchase '||item.name||' @ '|| location.name||' from '||itemsupplier.supplier_id,
      location.name as location_id,
      'purchase' as type,
      priority,
      jsonb_build_object(item.name||' @ '|| location.name,1),
      case when itemsupplier.resource_id is not null then jsonb_build_object(itemsupplier.resource_id, itemsupplier.resource_qty) else '{}'::jsonb end resources,
      itemsupplier.leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemsupplier.sizeminimum,
                               'operation_multiple', itemsupplier.sizemultiple,
                               'operation_max', itemsupplier.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemsupplier
      inner join item i_parent on i_parent.name = itemsupplier.item_id
      inner join item on item.name = %s and item.lft between i_parent.lft and i_parent.rght
      inner join location l_parent on l_parent.name = itemsupplier.location_id
      inner join location on location.lft between l_parent.lft and l_parent.rght
      union all
      select 'Purchase '||item.name||' @ '|| location.name||' from '||itemsupplier.supplier_id,
      location.name as location_id,
      'purchase' as type,
      priority,
      jsonb_build_object(item.name||' @ '|| location.name,1),
      case when itemsupplier.resource_id is not null then jsonb_build_object(itemsupplier.resource_id, itemsupplier.resource_qty) else '{}'::jsonb end resources,
      itemsupplier.leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemsupplier.sizeminimum,
                               'operation_multiple', itemsupplier.sizemultiple,
                               'operation_max', itemsupplier.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemsupplier
      inner join item i_parent on i_parent.name = itemsupplier.item_id
      inner join item on item.name = %s and item.lft between i_parent.lft and i_parent.rght
      inner join location on location.lft = location.rght - 1
      where location_id is null
      """
            )

        query = (
            query + " order by grandparentoperation, parentoperation, sibling_priority"
        )

        if downstream:
            cursor.execute(query, (item_name,) * 2)
        else:
            cursor.execute(query, (item_name,) * 7)

        for i in cursor.fetchall():
            for j in reportclass.processRecord(i, request, depth, downstream, None, 1):
                yield j

    @classmethod
    def getOperationFromResource(
        reportclass, request, resource_name, downstream, depth
    ):
        cursor = connections[request.database].cursor()
        query = """
      -- MANUFACTURING OPERATIONS
      select distinct
      case when parentoperation is null then operation else sibling end,
      case when parentoperation is null then operation_location else sibling_location end,
      case when parentoperation is null then operation_type else sibling_type end,
      case when parentoperation is null then operation_priority else sibling_priority end,
      case when parentoperation is null then operation_om else sibling_om end,
      case when parentoperation is null then operation_or else sibling_or end,
      case when parentoperation is null then operation_duration else sibling_duration end,
      case when parentoperation is null then operation_duration_per else sibling_duration_per end,
      parentoperation,
      parentoperation_type,
      parentoperation_priority,
      grandparentoperation,
      grandparentoperation_type,
      grandparentoperation_priority,
      sizes,
      grandparentitem_name,
      parentitem_name,
      item_name,
      grandparentitem_description,
      parentitem_description,
      item_description
       from
      (
      select operation.name as operation,
           operation.type operation_type,
           operation.location_id operation_location,
           operation.priority as operation_priority,
           operation.duration as operation_duration,
           operation.duration_per as operation_duration_per,
           case when operation.item_id is not null then jsonb_build_object(operation.item_id||' @ '||operation.location_id, 1) else '{}'::jsonb end
           ||jsonb_object_agg(operationmaterial.item_id||' @ '||operation.location_id,
                              coalesce(operationmaterial.quantity, operationmaterial.quantity_fixed, 0)) filter (where operationmaterial.id is not null) as operation_om,
           jsonb_object_agg(operationresource.resource_id, operationresource.quantity) filter (where operationresource.id is not null) as operation_or,
             parentoperation.name as parentoperation,
           parentoperation.type as parentoperation_type,
           parentoperation.priority parentoperation_priority,
             sibling.name as sibling,
           sibling.type as sibling_type,
           sibling.location_id as sibling_location,
           sibling.priority as sibling_priority,
           sibling.duration as sibling_duration,
           sibling.duration_per as sibling_duration_per,
           case when grandparentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(grandparentoperation.item_id||' @ '||grandparentoperation.location_id, 1) else '{}'::jsonb end
           ||case when parentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(parentoperation.item_id||' @ '||parentoperation.location_id, 1) else '{}'::jsonb end
           ||case when sibling.item_id is not null then jsonb_build_object(sibling.item_id||' @ '||sibling.location_id, 1) else '{}'::jsonb end
           || coalesce(jsonb_object_agg(siblingoperationmaterial.item_id||' @ '||sibling.location_id,
                                        coalesce(siblingoperationmaterial.quantity, siblingoperationmaterial.quantity_fixed, 0)) filter (where siblingoperationmaterial.id is not null), '{}'::jsonb) as sibling_om,
           jsonb_object_agg(siblingoperationresource.resource_id, siblingoperationresource.quantity)filter (where siblingoperationresource.id is not null) as sibling_or,
             grandparentoperation.name as grandparentoperation,
           grandparentoperation.type as grandparentoperation_type,
           grandparentoperation.priority as grandparentoperation_priority,
           jsonb_build_object( 'operation_min', operation.sizeminimum,
                               'operation_multiple', operation.sizemultiple,
                               'operation_max', operation.sizemaximum,
                               'parentoperation_min', parentoperation.sizeminimum,
                               'parentoperation_multiple',parentoperation.sizemultiple,
                               'parentoperation_max', parentoperation.sizemaximum,
                               'grandparentoperation_min', grandparentoperation.sizeminimum,
                               'grandparentoperation_multiple', grandparentoperation.sizemultiple,
                               'grandparentoperation_max', grandparentoperation.sizemaximum) as sizes,
           grandparentitem.name as grandparentitem_name,
           parentitem.name as parentitem_name,
           item.name as item_name,
           grandparentitem.description as grandparentitem_description,
           parentitem.description as parentitem_description,
           item.description as item_description
      from operation
      left outer join operationmaterial on operationmaterial.operation_id = operation.name
      left outer join operationresource on operationresource.operation_id = operation.name
      left outer join operation parentoperation on parentoperation.name = operation.owner_id
      left outer join operation grandparentoperation on grandparentoperation.name = parentoperation.owner_id
      left outer join operation sibling on sibling.owner_id = parentoperation.name
      left outer join operationmaterial siblingoperationmaterial on siblingoperationmaterial.operation_id = sibling.name
      left outer join operationresource siblingoperationresource on siblingoperationresource.operation_id = sibling.name
      left outer join item grandparentitem on grandparentitem.name = grandparentoperation.item_id
      left outer join item parentitem on parentitem.name = parentoperation.item_id
      left outer join item on item.name = coalesce(operation.item_id,
                                                   (select item_id from operationmaterial where operation_id = operation.name and quantity > 0 limit 1))
      where operation.type in ('time_per','fixed_time')
      and %s
      group by operation.name, parentoperation.name, sibling.name, grandparentoperation.name,
      grandparentitem.name, parentitem.name, item.name, grandparentitem.description, parentitem.description, item.description
      ) t
      union all
      -- DISTRIBUTION OPERATIONS
      select 'Ship '||item.name||' from '||itemdistribution.origin_id||' to '||itemdistribution.location_id,
      itemdistribution.location_id,
      'distribution' as type,
      priority,
      jsonb_build_object(item.name||' @ '||itemdistribution.origin_id, -1,
                         item.name||' @ '||itemdistribution.location_id, 1) as operation_om,
      case when itemdistribution.resource_id is not null
      then jsonb_build_object(itemdistribution.resource_id, itemdistribution.resource_qty)
      else '{}'::jsonb end operation_or,
      leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemdistribution.sizeminimum,
                               'operation_multiple', itemdistribution.sizemultiple,
                               'operation_max', itemdistribution.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemdistribution
      inner join item parent on parent.name = itemdistribution.item_id
      inner join item on item.lft between parent.lft and parent.rght
      where itemdistribution.resource_id = %%s
      union all
      -- PURCHASING OPERATIONS
      select 'Purchase '||item.name||' @ '|| location.name||' from '||itemsupplier.supplier_id,
      location.name as location_id,
      'purchase' as type,
      priority,
      jsonb_build_object(item.name||' @ '|| location.name,1),
      case when itemsupplier.resource_id is not null then jsonb_build_object(itemsupplier.resource_id, itemsupplier.resource_qty) else '{}'::jsonb end resources,
      itemsupplier.leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemsupplier.sizeminimum,
                               'operation_multiple', itemsupplier.sizemultiple,
                               'operation_max', itemsupplier.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemsupplier
      inner join item i_parent on i_parent.name = itemsupplier.item_id
      inner join item on item.lft between i_parent.lft and i_parent.rght
      inner join location l_parent on l_parent.name = itemsupplier.location_id
      inner join location on location.lft between l_parent.lft and l_parent.rght
      where itemsupplier.resource_id = %%s
      union all
      select 'Purchase '||item.name||' @ '|| location.name||' from '||itemsupplier.supplier_id,
      location.name as location_id,
      'purchase' as type,
      priority,
      jsonb_build_object(item.name||' @ '|| location.name,1),
      case when itemsupplier.resource_id is not null then jsonb_build_object(itemsupplier.resource_id, itemsupplier.resource_qty) else '{}'::jsonb end resources,
      itemsupplier.leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemsupplier.sizeminimum,
                               'operation_multiple', itemsupplier.sizemultiple,
                               'operation_max', itemsupplier.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemsupplier
      inner join item i_parent on i_parent.name = itemsupplier.item_id
      inner join item on item.lft between i_parent.lft and i_parent.rght
      inner join location on location.lft = location.rght - 1
      where location_id is null and itemsupplier.resource_id = %%s
      order by grandparentoperation, parentoperation, sibling_priority
      """ % (
            "operationresource.resource_id = %s"
            if not downstream
            else "exists (select 1 from operationresource where operation_id = operation.name and resource_id = %s)"
        )

        cursor.execute(query, (resource_name,) * 4)

        for i in cursor.fetchall():
            for j in reportclass.processRecord(i, request, depth, downstream, None, 1):
                yield j

    @classmethod
    def getOperationFromName(reportclass, request, operation_name, downstream, depth):
        cursor = connections[request.database].cursor()
        query = """
      -- MANUFACTURING OPERATIONS
      select distinct
      case when parentoperation is null then operation else sibling end,
      case when parentoperation is null then operation_location else sibling_location end,
      case when parentoperation is null then operation_type else sibling_type end,
      case when parentoperation is null then operation_priority else sibling_priority end,
      case when parentoperation is null then operation_om else sibling_om end,
      case when parentoperation is null then operation_or else sibling_or end,
      case when parentoperation is null then operation_duration else sibling_duration end,
      case when parentoperation is null then operation_duration_per else sibling_duration_per end,
      parentoperation,
      parentoperation_type,
      parentoperation_priority,
      grandparentoperation,
      grandparentoperation_type,
      grandparentoperation_priority,
      sizes,
      grandparentitem_name,
      parentitem_name,
      item_name,
      grandparentitem_description,
      parentitem_description,
      item_description
       from
      (
      select operation.name as operation,
           operation.type operation_type,
           operation.location_id operation_location,
           operation.priority as operation_priority,
           operation.duration as operation_duration,
           operation.duration_per as operation_duration_per,
           case when operation.item_id is not null then jsonb_build_object(operation.item_id||' @ '||operation.location_id, 1) else '{}'::jsonb end
           ||jsonb_object_agg(operationmaterial.item_id||' @ '||operation.location_id,
                              coalesce(operationmaterial.quantity, operationmaterial.quantity_fixed, 0)) filter (where operationmaterial.id is not null) as operation_om,
           jsonb_object_agg(operationresource.resource_id, operationresource.quantity) filter (where operationresource.id is not null) as operation_or,
             parentoperation.name as parentoperation,
           parentoperation.type as parentoperation_type,
           parentoperation.priority parentoperation_priority,
             sibling.name as sibling,
           sibling.type as sibling_type,
           sibling.location_id as sibling_location,
           sibling.priority as sibling_priority,
           sibling.duration as sibling_duration,
           sibling.duration_per as sibling_duration_per,
           case when grandparentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(grandparentoperation.item_id||' @ '||grandparentoperation.location_id, 1) else '{}'::jsonb end
           ||case when parentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(parentoperation.item_id||' @ '||parentoperation.location_id, 1) else '{}'::jsonb end
           ||case when sibling.item_id is not null then jsonb_build_object(sibling.item_id||' @ '||sibling.location_id, 1) else '{}'::jsonb end
           ||coalesce(jsonb_object_agg(siblingoperationmaterial.item_id||' @ '||sibling.location_id,
                                       coalesce(siblingoperationmaterial.quantity, siblingoperationmaterial.quantity_fixed, 0)) filter (where siblingoperationmaterial.id is not null), '{}'::jsonb) as sibling_om,
           jsonb_object_agg(siblingoperationresource.resource_id, siblingoperationresource.quantity)filter (where siblingoperationresource.id is not null) as sibling_or,
             grandparentoperation.name as grandparentoperation,
           grandparentoperation.type as grandparentoperation_type,
           grandparentoperation.priority as grandparentoperation_priority,
           jsonb_build_object( 'operation_min', operation.sizeminimum,
                               'operation_multiple', operation.sizemultiple,
                               'operation_max', operation.sizemaximum,
                               'parentoperation_min', parentoperation.sizeminimum,
                               'parentoperation_multiple',parentoperation.sizemultiple,
                               'parentoperation_max', parentoperation.sizemaximum,
                               'grandparentoperation_min', grandparentoperation.sizeminimum,
                               'grandparentoperation_multiple', grandparentoperation.sizemultiple,
                               'grandparentoperation_max', grandparentoperation.sizemaximum) as sizes,
           grandparentitem.name as grandparentitem_name,
           parentitem.name as parentitem_name,
           item.name as item_name,
           grandparentitem.description as grandparentitem_description,
           parentitem.description as parentitem_description,
           item.description as item_description
      from operation
      left outer join operationmaterial on operationmaterial.operation_id = operation.name
      left outer join operationresource on operationresource.operation_id = operation.name
      left outer join operation parentoperation on parentoperation.name = operation.owner_id
      left outer join operation grandparentoperation on grandparentoperation.name = parentoperation.owner_id
      left outer join operation sibling on sibling.owner_id = parentoperation.name
      left outer join operationmaterial siblingoperationmaterial on siblingoperationmaterial.operation_id = sibling.name
      left outer join operationresource siblingoperationresource on siblingoperationresource.operation_id = sibling.name
      left outer join item grandparentitem on grandparentitem.name = grandparentoperation.item_id
      left outer join item parentitem on parentitem.name = parentoperation.item_id
      left outer join item on item.name = coalesce(operation.item_id,
                                                   (select item_id from operationmaterial where operation_id = operation.name and quantity > 0 limit 1))
      where operation.type in ('time_per','fixed_time')
      and (operation.name = %s or parentoperation.name = %s or grandparentoperation.name = %s)
      group by operation.name, parentoperation.name, sibling.name, grandparentoperation.name,
      grandparentitem.name, parentitem.name, item.name, grandparentitem.description, parentitem.description, item.description
      ) t
      order by grandparentoperation, parentoperation, sibling_priority
      """

        cursor.execute(query, (operation_name,) * 3)

        for i in cursor.fetchall():
            for j in reportclass.processRecord(i, request, depth, downstream, None, 1):
                yield j

    @classmethod
    def getOperationFromBuffer(
        reportclass,
        request,
        buffer_name,
        downstream,
        depth,
        previousOperation,
        bom_quantity,
    ):
        cursor = connections[request.database].cursor()
        item = buffer_name[0 : buffer_name.find(" @ ")]
        location = buffer_name[buffer_name.find(" @ ") + 3 :]
        query = """
      -- MANUFACTURING OPERATIONS
      select distinct
      case when parentoperation is null then operation else sibling end,
      case when parentoperation is null then operation_location else sibling_location end,
      case when parentoperation is null then operation_type else sibling_type end,
      case when parentoperation is null then operation_priority else sibling_priority end,
      case when parentoperation is null then operation_om else sibling_om end,
      case when parentoperation is null then operation_or else sibling_or end,
      case when parentoperation is null then operation_duration else sibling_duration end,
      case when parentoperation is null then operation_duration_per else sibling_duration_per end,
      parentoperation,
      parentoperation_type,
      parentoperation_priority,
      grandparentoperation,
      grandparentoperation_type,
      grandparentoperation_priority,
      sizes,
      grandparentitem_name,
      parentitem_name,
      item_name,
      grandparentitem_description,
      parentitem_description,
      item_description
       from
      (
      select operation.name as operation,
           operation.type operation_type,
           operation.location_id operation_location,
           operation.priority as operation_priority,
           operation.duration as operation_duration,
           operation.duration_per as operation_duration_per,
           case when operation.item_id is not null then jsonb_build_object(operation.item_id||' @ '||operation.location_id, 1) else '{}'::jsonb end
           ||jsonb_object_agg(operationmaterial.item_id||' @ '||operation.location_id,
                              coalesce(operationmaterial.quantity, operationmaterial.quantity_fixed, 0)) filter (where operationmaterial.id is not null) as operation_om,
           jsonb_object_agg(operationresource.resource_id, operationresource.quantity) filter (where operationresource.id is not null) as operation_or,
             parentoperation.name as parentoperation,
           parentoperation.type as parentoperation_type,
           parentoperation.priority parentoperation_priority,
             sibling.name as sibling,
           sibling.type as sibling_type,
           sibling.location_id as sibling_location,
           sibling.priority as sibling_priority,
           sibling.duration as sibling_duration,
           sibling.duration_per as sibling_duration_per,
           case when grandparentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(grandparentoperation.item_id||' @ '||grandparentoperation.location_id, 1) else '{}'::jsonb end
           ||case when parentoperation.item_id is not null
           and sibling.priority = (select max(priority) from operation where owner_id = parentoperation.name)
           then jsonb_build_object(parentoperation.item_id||' @ '||parentoperation.location_id, 1) else '{}'::jsonb end
           ||case when sibling.item_id is not null then jsonb_build_object(sibling.item_id||' @ '||sibling.location_id, 1) else '{}'::jsonb end
           ||coalesce(jsonb_object_agg(siblingoperationmaterial.item_id||' @ '||sibling.location_id,
                                       coalesce(siblingoperationmaterial.quantity, siblingoperationmaterial.quantity_fixed, 0)) filter (where siblingoperationmaterial.id is not null), '{}'::jsonb) as sibling_om,
           jsonb_object_agg(siblingoperationresource.resource_id, siblingoperationresource.quantity)filter (where siblingoperationresource.id is not null) as sibling_or,
             grandparentoperation.name as grandparentoperation,
           grandparentoperation.type as grandparentoperation_type,
           grandparentoperation.priority as grandparentoperation_priority,
           jsonb_build_object( 'operation_min', operation.sizeminimum,
                               'operation_multiple', operation.sizemultiple,
                               'operation_max', operation.sizemaximum,
                               'parentoperation_min', parentoperation.sizeminimum,
                               'parentoperation_multiple',parentoperation.sizemultiple,
                               'parentoperation_max', parentoperation.sizemaximum,
                               'grandparentoperation_min', grandparentoperation.sizeminimum,
                               'grandparentoperation_multiple', grandparentoperation.sizemultiple,
                               'grandparentoperation_max', grandparentoperation.sizemaximum) as sizes,
           grandparentitem.name as grandparentitem_name,
           parentitem.name as parentitem_name,
           item.name as item_name,
           grandparentitem.description as grandparentitem_description,
           parentitem.description as parentitem_description,
           item.description as item_description
      from operation
      left outer join operationmaterial on operationmaterial.operation_id = operation.name
      left outer join operationresource on operationresource.operation_id = operation.name
      left outer join operation parentoperation on parentoperation.name = operation.owner_id
      left outer join operation grandparentoperation on grandparentoperation.name = parentoperation.owner_id
      left outer join operation sibling on sibling.owner_id = parentoperation.name
      left outer join operationmaterial siblingoperationmaterial on siblingoperationmaterial.operation_id = sibling.name
      left outer join operationresource siblingoperationresource on siblingoperationresource.operation_id = sibling.name
      left outer join item grandparentitem on grandparentitem.name = grandparentoperation.item_id
      left outer join item parentitem on parentitem.name = parentoperation.item_id
      left outer join item on item.name = coalesce(operation.item_id,
                                                   (select item_id from operationmaterial where operation_id = operation.name and quantity > 0 limit 1))
      where operation.type in ('time_per','fixed_time')
      and operation.location_id = %%s
      %s
      group by operation.name, parentoperation.name, sibling.name, grandparentoperation.name,
      grandparentitem.name, parentitem.name, item.name, grandparentitem.description, parentitem.description, item.description
      ) t
      union all
      -- DISTRIBUTION OPERATIONS
      select 'Ship '||item.name||' from '||itemdistribution.origin_id||' to '||itemdistribution.location_id,
      itemdistribution.location_id,
      'distribution' as type,
      priority,
      jsonb_build_object(item.name||' @ '||itemdistribution.origin_id, -1,
                         item.name||' @ '||itemdistribution.location_id, 1) as operation_om,
      case when itemdistribution.resource_id is not null
      then jsonb_build_object(itemdistribution.resource_id, itemdistribution.resource_qty)
      else '{}'::jsonb end operation_or,
      leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemdistribution.sizeminimum,
                               'operation_multiple', itemdistribution.sizemultiple,
                               'operation_max', itemdistribution.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemdistribution
      inner join item parent on parent.name = itemdistribution.item_id
      inner join item on item.name = %%s and item.lft between parent.lft and parent.rght
      where itemdistribution.%s = %%s
      """ % (
            (
                """
                and (operation.item_id = %s or
                (exists (select 1 from operationmaterial op1 where op1.operation_id = operation.name and op1.item_id = %s and op1.quantity > 0))
                or parentoperation.item_id = %s
                or grandparentoperation.item_id = %s)
                """,
                "location_id",
            )
            if not downstream
            else (
                """
                and exists (select 1 from operationmaterial om where om.operation_id = operation.name
                and om.item_id = %s and om.quantity < 0)
                """,
                "origin_id",
            )
        )

        if not downstream:
            query = (
                query
                + """
        union all
      -- PURCHASING OPERATIONS
      select 'Purchase '||item.name||' @ '|| location.name||' from '||itemsupplier.supplier_id,
      location.name as location_id,
      'purchase' as type,
      priority,
      jsonb_build_object(item.name||' @ '|| location.name,1),
      case when itemsupplier.resource_id is not null then jsonb_build_object(itemsupplier.resource_id, itemsupplier.resource_qty) else '{}'::jsonb end resources,
      itemsupplier.leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemsupplier.sizeminimum,
                               'operation_multiple', itemsupplier.sizemultiple,
                               'operation_max', itemsupplier.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemsupplier
      inner join item i_parent on i_parent.name = itemsupplier.item_id
      inner join item on item.name = %s and item.lft between i_parent.lft and i_parent.rght
      inner join location l_parent on l_parent.name = itemsupplier.location_id
      inner join location on location.name = %s and location.lft between l_parent.lft and l_parent.rght
      union all
      select 'Purchase '||item.name||' @ '|| location.name||' from '||itemsupplier.supplier_id,
      location.name as location_id,
      'purchase' as type,
      priority,
      jsonb_build_object(item.name||' @ '|| location.name,1),
      case when itemsupplier.resource_id is not null then jsonb_build_object(itemsupplier.resource_id, itemsupplier.resource_qty) else '{}'::jsonb end resources,
      itemsupplier.leadtime as duration,
      null as duration_per,
      null,
      null,
      null,
      null,
      null,
      null,
      jsonb_build_object( 'operation_min', itemsupplier.sizeminimum,
                               'operation_multiple', itemsupplier.sizemultiple,
                               'operation_max', itemsupplier.sizemaximum) as sizes,
      null,
      null,
      item.name,
      null,
      null,
      item.description
      from itemsupplier
      inner join item i_parent on i_parent.name = itemsupplier.item_id
      inner join item on item.name = %s and item.lft between i_parent.lft and i_parent.rght
      inner join location on location.name = %s and location.lft = location.rght - 1
      where location_id is null
      """
            )

        query = (
            query + " order by grandparentoperation, parentoperation, sibling_priority"
        )

        if downstream:
            cursor.execute(query, (location, item, item, location))
        else:
            cursor.execute(
                query,
                (
                    location,
                    item,
                    item,
                    item,
                    item,
                    item,
                    location,
                    item,
                    location,
                    item,
                    location,
                ),
            )

        for i in cursor.fetchall():
            for j in reportclass.processRecord(
                i, request, depth, downstream, previousOperation, bom_quantity
            ):
                yield j

    @classmethod
    def processRecord(
        reportclass, i, request, depth, downstream, previousOperation, bom_quantity
    ):

        # First can we go further ?
        if len(reportclass.node_count) > 400:
            return

        # do we have a grandparentoperation
        if i[11] and not i[11] in reportclass.operation_dict:
            reportclass.operation_id = reportclass.operation_id + 1
            reportclass.operation_dict[i[11]] = reportclass.operation_id
            if i[11] not in reportclass.suboperations_count_dict:
                reportclass.suboperations_count_dict[i[11]] = Operation.objects.filter(
                    owner_id=i[11]
                ).count()
            grandparentoperation = {
                "depth": depth * 2,
                "id": reportclass.operation_id,
                "operation": i[11],
                "priority": i[13],
                "type": i[12],
                "item": i[15],
                "description": i[18],
                "location": i[1],
                "resources": None,
                "parentoper": None,
                "suboperation": 0,
                "duration": None,
                "duration_per": None,
                "quantity": 1,
                "buffers": None,
                "parent": (
                    reportclass.operation_dict[previousOperation]
                    if previousOperation
                    else None
                ),
                "leaf": "false",
                "expanded": "true",
                "numsuboperations": reportclass.suboperations_count_dict[i[11]],
                "realdepth": -depth if reportclass.downstream else depth,
                "sizeminimum": i[14]["grandparentoperation_min"],
                "sizemaximum": i[14]["grandparentoperation_max"],
                "sizemultiple": i[14]["grandparentoperation_multiple"],
                "alternate": "false",
            }
            reportclass.node_count.add(i[11])
            yield grandparentoperation

        # do we have a parent operation
        if i[8] and not i[8] in reportclass.operation_dict:
            reportclass.operation_id = reportclass.operation_id + 1
            reportclass.operation_dict[i[8]] = reportclass.operation_id
            if i[8] not in reportclass.suboperations_count_dict:
                reportclass.suboperations_count_dict[i[8]] = Operation.objects.filter(
                    owner_id=i[8]
                ).count()
            if i[11]:
                if i[11] in reportclass.parent_count_dict:
                    reportclass.parent_count_dict[i[11]] = (
                        reportclass.parent_count_dict[i[11]] + 1
                    )
                else:
                    reportclass.parent_count_dict[i[11]] = 1
            parentoperation = {
                "depth": depth * 2,
                "id": reportclass.operation_id,
                "operation": i[8],
                "type": i[9],
                "item": i[16],
                "description": i[19],
                "priority": i[10],
                "location": i[1],
                "resources": None,
                "parentoper": i[11],
                "suboperation": -reportclass.parent_count_dict[i[11]] if i[11] else 0,
                "duration": None,
                "duration_per": None,
                "quantity": 1,
                "buffers": None,
                "parent": reportclass.operation_dict[i[11]]
                if i[11]
                else (
                    reportclass.operation_dict[previousOperation]
                    if previousOperation
                    else None
                ),
                "leaf": "false",
                "expanded": "true",
                "numsuboperations": reportclass.suboperations_count_dict[i[8]],
                "realdepth": -depth if reportclass.downstream else depth,
                "sizeminimum": i[14]["parentoperation_min"],
                "sizemaximum": i[14]["parentoperation_max"],
                "sizemultiple": i[14]["parentoperation_multiple"],
                "alternate": "false",
            }
            reportclass.node_count.add(i[8])
            yield parentoperation

        # go through the regular time_per/fixed_time operation
        if i[0] not in reportclass.operation_dict:
            reportclass.operation_id = reportclass.operation_id + 1
            reportclass.operation_dict[i[0]] = reportclass.operation_id
            if i[8]:
                if i[8] in reportclass.parent_count_dict:
                    reportclass.parent_count_dict[i[8]] = (
                        reportclass.parent_count_dict[i[8]] + 1
                    )
                else:
                    reportclass.parent_count_dict[i[8]] = 1
            operation = {
                "depth": depth * 2 if not i[8] else depth * 2 + 1,
                "id": reportclass.operation_id,
                "operation": i[0],
                "priority": i[3],
                "type": i[2],
                "item": i[17],
                "description": i[20],
                "location": i[1],
                "resources": tuple(i[5].items()) if i[5] else None,
                "parentoper": i[8],
                "suboperation": 0
                if not i[8]
                else (
                    reportclass.parent_count_dict[i[8]]
                    if i[9] == "routing"
                    else -reportclass.parent_count_dict[i[8]]
                ),
                "duration": i[6],
                "duration_per": i[7],
                "quantity": bom_quantity,
                "buffers": tuple(i[4].items()) if i[4] else None,
                "parent": reportclass.operation_dict[i[8]]
                if i[8]
                else (
                    reportclass.operation_dict[previousOperation]
                    if previousOperation
                    else None
                ),
                "leaf": "false",
                "expanded": "true",
                "numsuboperations": 0,
                "realdepth": -depth if reportclass.downstream else depth,
                "sizeminimum": i[14]["operation_min"],
                "sizemaximum": i[14]["operation_max"],
                "sizemultiple": i[14]["operation_multiple"],
                "alternate": "false",
                "alternate_priority": (i[13] or i[10] or i[3] or 999),
                "alternate_operation": (i[11] or i[8] or i[0]),
            }
            reportclass.node_count.add(i[0])
            yield operation

        if i[5]:
            for resource, quantity in tuple(i[5].items()):
                reportclass.node_count.add(resource)

        if i[4]:
            for buffer, quantity in tuple(i[4].items()):

                # I might already have visisted that buffer
                if buffer in reportclass.node_count:
                    continue
                reportclass.node_count.add(buffer)
                if float(quantity) < 0 and not downstream:
                    yield from reportclass.getOperationFromBuffer(
                        request, buffer, downstream, depth + 1, i[0], float(quantity)
                    )
                elif float(quantity) > 0 and downstream:
                    yield from reportclass.getOperationFromBuffer(
                        request, buffer, downstream, depth + 1, i[0], float(quantity)
                    )

    @classmethod
    def query(reportclass, request, basequery):
        """
        A function that recurses upstream or downstream in the supply chain.
        """
        # Update item and location hierarchies
        Item.rebuildHierarchy(database=request.database)
        Location.rebuildHierarchy(database=request.database)

        # dictionary to retrieve the operation id from its name
        reportclass.operation_dict = {}

        # counter used to give a unique id to the operation
        reportclass.operation_id = 0

        # dictionary to count the number of suboperations
        # prevents to hit database more than once for a given routing/alternate
        reportclass.suboperations_count_dict = {}

        # dictionary to reassign a priority to the alternate/routing suboperations
        # required otherwise suboperations with same priority overlap.
        reportclass.parent_count_dict = {}

        # set used to count the number of nodes in the graph.
        # we stop at 400 otherwise we could draw the full supply chain
        # in the case of downstream raw material.
        reportclass.node_count = set()

        results = []

        if str(reportclass.objecttype._meta) == "input.buffer":
            buffer_name = basequery.query.get_compiler(basequery.db).as_sql(
                with_col_aliases=False
            )[1][0]
            if " @ " not in buffer_name:
                b = Buffer.objects.get(id=buffer_name)
                buffer_name = "%s @ %s" % (b.item.name, b.location.name)

            for i in reportclass.getOperationFromBuffer(
                request, buffer_name, reportclass.downstream, 0, None, 1
            ):
                results.append(i)
        elif str(reportclass.objecttype._meta) == "input.demand":
            demand_name = basequery.query.get_compiler(basequery.db).as_sql(
                with_col_aliases=False
            )[1][0]
            d = Demand.objects.get(name=demand_name)
            if d.operation is None:
                buffer_name = "%s @ %s" % (d.item.name, d.location.name)

                for i in reportclass.getOperationFromBuffer(
                    request,
                    buffer_name,
                    reportclass.downstream,
                    depth=0,
                    previousOperation=None,
                    bom_quantity=1,
                ):
                    results.append(i)
            else:
                operation_name = d.operation.name

                for i in reportclass.getOperationFromName(
                    request, operation_name, reportclass.downstream, depth=0
                ):
                    results.append(i)
        elif str(reportclass.objecttype._meta) == "input.resource":
            resource_name = basequery.query.get_compiler(basequery.db).as_sql(
                with_col_aliases=False
            )[1][0]

            for i in reportclass.getOperationFromResource(
                request, resource_name, reportclass.downstream, depth=0
            ):
                results.append(i)
        elif str(reportclass.objecttype._meta) == "input.operation":
            operation_name = basequery.query.get_compiler(basequery.db).as_sql(
                with_col_aliases=False
            )[1][0]

            for i in reportclass.getOperationFromName(
                request, operation_name, reportclass.downstream, depth=0
            ):
                results.append(i)
        elif str(reportclass.objecttype._meta) == "input.item":
            item_name = basequery.query.get_compiler(basequery.db).as_sql(
                with_col_aliases=False
            )[1][0]

            for i in reportclass.getOperationFromItem(
                request, item_name, reportclass.downstream, depth=0
            ):
                results.append(i)
        else:
            raise Exception("Supply path for an unknown entity")

        # post-process results to calculate leaf field
        parents = [i["parent"] for i in results if i["parent"]]
        for i in results:
            if i["type"] in ["time_per", "fixed_time", "purchase", "distribution"]:
                i["leaf"] = "true" if i["id"] not in parents else "false"
            else:
                i["leaf"] = "false"

        # post-process results for alternate operations
        # a first loop to find the min priority
        d = {}
        for i in results:
            if i["buffers"]:
                for j in i["buffers"]:
                    if j[1] > 0:
                        d[j[0]] = (
                            i["alternate_priority"]
                            if j[0] not in d
                            else min(i["alternate_priority"], d[j[0]])
                        )
        # a second loop to find alternate operations
        alternate_ops = []
        for i in results:
            if i["buffers"]:
                for j in i["buffers"]:
                    if j[1] > 0 and i["alternate_priority"] > d[j[0]]:
                        alternate_ops.append(i["alternate_operation"])

        # a third loop to set the alternate flag
        for i in results:
            if i["type"] not in ("purchase", "distribution", "time_per", "fixed_time"):
                continue
            if (i["operation"] in alternate_ops and not i["parentoper"]) or (
                i["parentoper"] and i["parentoper"] in alternate_ops
            ):
                i["alternate"] = "true"

        for i in results:
            yield i


class UpstreamDemandPath(PathReport):
    downstream = False
    objecttype = Demand


class UpstreamItemPath(PathReport):
    downstream = False
    objecttype = Item


class UpstreamBufferPath(PathReport):
    downstream = False
    objecttype = Buffer

    @classmethod
    def getRoot(reportclass, request, entity):
        from django.core.exceptions import ObjectDoesNotExist

        try:
            buf = (
                Buffer.objects.using(request.database)
                .annotate(name=RawSQL("item_id||' @ '||location_id", ()))
                .get(name=entity)
            )
            if reportclass.downstream:
                return reportclass.findUsage(buf, request.database, 0, 1, 0, True)
            else:
                return reportclass.findReplenishment(
                    buf, request.database, 0, 1, 0, True
                )
        except ObjectDoesNotExist:
            raise Http404("buffer %s doesn't exist" % entity)


class UpstreamResourcePath(PathReport):
    downstream = False
    objecttype = Resource

    @classmethod
    def getRoot(reportclass, request, entity):
        from django.core.exceptions import ObjectDoesNotExist

        try:
            root = Resource.objects.using(request.database).get(name=entity)
        except ObjectDoesNotExist:
            raise Http404("resource %s doesn't exist" % entity)
        return [
            (
                0,
                None,
                i.operation,
                1,
                0,
                None,
                0,
                True,
                i.operation.location.name if i.operation.location else None,
            )
            for i in root.operationresources.using(request.database).all()
        ]


class UpstreamOperationPath(PathReport):
    downstream = False
    objecttype = Operation


class DownstreamItemPath(UpstreamItemPath):
    downstream = True
    objecttype = Item
    title = _("where used")


class DownstreamDemandPath(UpstreamDemandPath):
    downstream = True
    objecttype = Demand
    title = _("where used")


class DownstreamBufferPath(UpstreamBufferPath):
    downstream = True
    objecttype = Buffer
    title = _("where used")


class DownstreamResourcePath(UpstreamResourcePath):
    downstream = True
    objecttype = Resource
    title = _("where used")


class DownstreamOperationPath(UpstreamOperationPath):
    downstream = True
    objecttype = Operation
    title = _("where used")


class OperationPlanDetail(View):
    def getData(self, request):
        current_date = getCurrentDate(request.database)
        cursor = connections[request.database].cursor()

        # Read the results from the database
        ids = request.GET.getlist("reference")
        first = True
        if not ids:
            yield "[]"
            raise StopIteration
        try:
            opplans = [
                x
                for x in OperationPlan.objects.all()
                .using(request.database)
                .filter(reference__in=ids)
                .select_related("operation")
            ]
            opplanmats = [
                x
                for x in OperationPlanMaterial.objects.all()
                .using(request.database)
                .filter(operationplan__reference__in=ids)
                .values()
            ]
            opplanrscs = [
                x
                for x in OperationPlanResource.objects.all()
                .using(request.database)
                .filter(operationplan__reference__in=ids)
                .values()
            ]
        except Exception as e:
            logger.error("Error retrieving operationplan data: %s" % e)
            yield "[]"
            raise StopIteration

        # Store my permissions
        view_PO = request.user.has_perm("input.view_purchaseorder")
        view_MO = request.user.has_perm("input.view_manufacturingorder")
        view_DO = request.user.has_perm("input.view_distributionorder")
        view_OpplanMaterial = request.user.has_perm("input.view_operationplanmaterial")
        view_OpplanResource = request.user.has_perm("input.view_operationplanresource")

        # Loop over all operationplans
        for opplan in opplans:

            # Check permissions
            if opplan.type == "DO" and not view_DO:
                continue
            if opplan.type == "PO" and not view_PO:
                continue
            if opplan.type == "MO" and not view_MO:
                continue
            try:
                # Base information
                res = {
                    "reference": opplan.reference,
                    "start": opplan.startdate.strftime("%Y-%m-%dT%H:%M:%S")
                    if opplan.startdate
                    else None,
                    "end": opplan.enddate.strftime("%Y-%m-%dT%H:%M:%S")
                    if opplan.enddate
                    else None,
                    "setupend": opplan.plan["setupend"].replace(" ", "T")
                    if "setupend" in opplan.plan
                    else None,
                    "quantity": float(opplan.quantity),
                    "quantity_completed": float(opplan.quantity_completed or 0),
                    "criticality": float(opplan.criticality)
                    if opplan.criticality
                    else "",
                    "delay": opplan.delay.total_seconds() if opplan.delay else "",
                    "status": opplan.status,
                    "type": opplan.type,
                    "name": opplan.name,
                    "destination": opplan.destination_id,
                    "location": opplan.location_id,
                    "origin": opplan.origin_id,
                    "supplier": opplan.supplier_id,
                    "item": opplan.item_id,
                    "color": float(opplan.color) if opplan.color else "",
                    "owner": opplan.owner.reference if opplan.owner else None,
                }
                if opplan.plan and "pegging" in opplan.plan:
                    res["pegging_demand"] = []
                    for d, q in opplan.plan["pegging"].items():
                        try:
                            obj = (
                                Demand.objects.all()
                                .using(request.database)
                                .only("name", "item", "due")
                                .get(name=d)
                            )
                            res["pegging_demand"].append(
                                {
                                    "demand": {
                                        "name": obj.name,
                                        "item": {"name": obj.item.name},
                                        "due": obj.due.strftime("%Y-%m-%dT%H:%M:%S"),
                                    },
                                    "quantity": q,
                                }
                            )
                        except Demand.DoesNotExist:
                            # Looks like this demand was deleted since the plan was generated
                            continue
                    res["pegging_demand"].sort(
                        key=lambda f: (f["demand"]["name"], f["demand"]["due"])
                    )
                if opplan.operation:
                    res["operation"] = {
                        "name": opplan.operation.name,
                        "type": "operation_%s" % opplan.operation.type,
                    }

                # Information on materials
                if view_OpplanMaterial:
                    # Retrieve information about eventual alternates
                    alts = {}
                    if opplan.operation:
                        cursor.execute(
                            """
                            select a.item_id, b.item_id
                            from operationmaterial a
                            inner join operationmaterial b on a.operation_id = b.operation_id and a.name = b.name
                            where a.operation_id = %s
                            and a.id != b.id
                            """,
                            (opplan.operation.name,),
                        )
                        for i in cursor.fetchall():
                            if i[0] not in alts:
                                alts[i[0]] = set()
                            alts[i[0]].add(i[1])
                    firstmat = True
                    for m in opplanmats:
                        if m["operationplan_id"] != opplan.reference:
                            continue
                        if firstmat:
                            firstmat = False
                            res["flowplans"] = []
                        flowplan = {
                            "date": m["flowdate"].strftime("%Y-%m-%dT%H:%M:%S"),
                            "quantity": float(m["quantity"]),
                            "onhand": float(m["onhand"] or 0),
                            "buffer": {
                                "item": m["item_id"],
                                "location": m["location_id"],
                            },
                        }
                        # List matching alternates
                        if m["item_id"] in alts:
                            flowplan["alternates"] = list(alts[m["item_id"]])
                        res["flowplans"].append(flowplan)

                # Information on resources
                if view_OpplanResource:
                    # Retrieve information about eventual alternates
                    alts = {}
                    if opplan.operation:
                        cursor.execute(
                            """
                            select res_children.name, alt_res_children.name
                            from operationresource
                            inner join resource
                              on  resource.name = operationresource.resource_id
                            inner join resource res_children
                              on  res_children.lft between resource.lft and resource.rght
                              and res_children.rght = res_children.lft + 1
                            inner join operationresource alt_opres
                              on ((operationresource.name is not null and operationresource.name = alt_opres.name)
                              or (operationresource.name is null and operationresource.id = alt_opres.id))
                              and operationresource.operation_id = alt_opres.operation_id
                            inner join resource alt_res
                              on alt_opres.resource_id = alt_res.name
                            inner join resource alt_res_children
                               on alt_res_children.lft between alt_res.lft and alt_res.rght
                               and alt_res_children.rght = alt_res_children.lft + 1
                            where (operationresource.skill_id is null or exists (
                               select 1 from resourceskill
                               where resourceskill.resource_id = alt_res_children.name
                               and resourceskill.skill_id = alt_opres.skill_id
                               ))
                            and operationresource.operation_id = %s
                            """,
                            (opplan.operation.name,),
                        )
                        for i in cursor.fetchall():
                            if i[0] not in alts:
                                alts[i[0]] = set()
                            alts[i[0]].add(i[1])
                    firstres = True
                    for m in opplanrscs:
                        if m["operationplan_id"] != opplan.reference:
                            continue
                        if firstres:
                            firstres = False
                            res["loadplans"] = []
                        ldplan = {
                            "date": m["startdate"].strftime("%Y-%m-%dT%H:%M:%S"),
                            "quantity": float(m["quantity"]),
                            "resource": {"name": m["resource_id"]},
                        }
                        # List matching alternates
                        for a in alts.values():
                            if m["resource_id"] in a:
                                t = [{"name": i} for i in a if i != m["resource_id"]]
                                if t:
                                    ldplan["alternates"] = t
                                break
                        res["loadplans"].append(ldplan)

                # Retrieve network status
                if opplan.item_id:
                    cursor.execute(
                        """
                        with items as (
                           select name from item where name = %s
                           )
                        select
                          items.name,
                          false,
                          location.name,
                          coalesce(onhand.qty,0) + coalesce(completed.quantity,0),
                          orders_plus.PO,
                          coalesce(orders_plus.DO, 0) - coalesce(orders_minus.DO, 0),
                          orders_plus.MO, sales.BO, sales.SO
                        from items
                        cross join location
                        left outer join (
                          select item_id, location_id, onhand as qty
                          from buffer
                          inner join items on items.name = buffer.item_id
                          ) onhand
                        on onhand.item_id = items.name and onhand.location_id = location.name
                        left outer join (
                           select opm.item_id, opm.location_id, sum(opm.quantity) as quantity
                           from operationplanmaterial opm
                           inner join operationplan op on opm.operationplan_id = op.reference
                           where op.status = 'completed'
                           group by opm.item_id, opm.location_id
                        ) completed
                        on completed.item_id = items.name and completed.location_id = location.name
                        left outer join (
                          select item_id, coalesce(location_id, destination_id) as location_id,
                          sum(case when type = 'MO' then quantity end) as MO,
                          sum(case when type = 'PO' then quantity end) as PO,
                          sum(case when type = 'DO' then quantity end) as DO
                          from operationplan
                          inner join items on items.name = operationplan.item_id
                          and status in ('approved', 'confirmed')
                          group by item_id, coalesce(location_id, destination_id)
                          ) orders_plus
                        on orders_plus.item_id = items.name and orders_plus.location_id = location.name
                        left outer join (
                          select item_id, origin_id as location_id,
                          sum(quantity) as DO
                          from operationplan
                          inner join items on items.name = operationplan.item_id
                          and status in ('approved', 'confirmed')
                          and type = 'DO'
                          group by item_id, origin_id
                          ) orders_minus
                        on orders_minus.item_id = items.name and orders_minus.location_id = location.name
                        left outer join (
                          select item_id, location_id,
                          sum(case when due < %s then quantity end) as BO,
                          sum(case when due >= %s then quantity end) as SO
                          from demand
                          inner join items on items.name = demand.item_id
                          where status in ('open', 'quote')
                          group by item_id, location_id
                          ) sales
                        on sales.item_id = items.name and sales.location_id = location.name
                        where
                          (coalesce(onhand.qty,0) + coalesce(completed.quantity,0)) > 0
                          or orders_plus.MO is not null
                          or orders_plus.PO is not null
                          or orders_plus.DO is not null
                          or orders_minus.DO is not null
                          or sales.BO is not null
                          or sales.SO is not null
                          or (items.name = %s and location.name = %s)
                        order by items.name, location.name
                        """,
                        (
                            opplan.item_id,
                            current_date,
                            current_date,
                            opplan.item_id,
                            opplan.location_id,
                        ),
                    )
                    res["network"] = []
                    for a in cursor.fetchall():
                        res["network"].append(
                            [
                                a[0],
                                a[1],
                                a[2],
                                float(a[3] or 0),
                                float(a[4] or 0),
                                float(a[5] or 0),
                                float(a[6] or 0),
                                float(a[7] or 0),
                                float(a[8] or 0),
                            ]
                        )

                # Downstream operationplans
                cursor.execute(
                    """
                    with cte as
                    (
                    select (value->>0)::int as level,
                    value->>1 as reference,
                    (value->>2)::numeric as quantity,
                    row_number() over() as rownum
                    from jsonb_array_elements((select plan->'downstream_opplans' from operationplan where reference = %%s))
                    )
                    select cte.level,
                    cte.reference,
                    operationplan.type,
                    case when operationplan.type = 'PO' then 'Purchase '||operationplan.item_id||' @ '||operationplan.location_id||' from '||operationplan.supplier_id
                         when operationplan.type = 'DO' then 'Ship '||operationplan.item_id||' from '||operationplan.origin_id||' to '||operationplan.destination_id
                         %s
                    else operationplan.operation_id end,
                    operationplan.status,
                    operationplan.item_id,
                    coalesce(operationplan.location_id, operationplan.destination_id),
                    to_char(operationplan.startdate,'YYYY-MM-DD hh24:mi:ss'),
                    to_char(operationplan.enddate,'YYYY-MM-DD hh24:mi:ss'),
                    trim(trailing '.' from (trim(trailing '0' from round(cte.quantity,8)::text)))||'/'||
                    trim(trailing '.' from (trim(trailing '0' from round(operationplan.quantity,8)::text)))
                    from cte
                    inner join operationplan on operationplan.reference = cte.reference
                    order by cte.rownum
                    """
                    % (
                        "when operationplan.demand_id is not null then 'Deliver '||operationplan.demand_id"
                        if "freppledb.forecast" not in settings.INSTALLED_APPS
                        else """
                        when coalesce(operationplan.demand_id, operationplan.forecast) is not null then 'Deliver '||coalesce(operationplan.demand_id, operationplan.forecast)
                        """
                    ),
                    (opplan.reference,),
                )

                if cursor.rowcount > 0:
                    res["downstreamoperationplans"] = []
                    for a in cursor.fetchall():
                        res["downstreamoperationplans"].append(
                            [
                                a[0],  # level
                                a[1],  # reference
                                a[2],  # type
                                a[3],  # operation
                                a[4],  # status
                                a[5],  # item
                                a[6],  # location
                                a[7],  # startdate
                                a[8],  # enddate
                                a[9],  # quantity,
                                0 if a[0] == 1 else 2,
                            ]
                        )

                # Upstream operationplans
                cursor.execute(
                    """
                    with cte as
                    (
                    select (value->>0)::int as level,
                    value->>1 as reference,
                    (value->>2)::numeric as quantity,
                    row_number() over() as rownum
                    from jsonb_array_elements((select plan->'upstream_opplans' from operationplan where reference = %s))
                    )
                    select cte.level,
                    cte.reference,
                    operationplan.type,
                    case when operationplan.type = 'PO' then 'Purchase '||operationplan.item_id||' @ '||operationplan.location_id||' from '||operationplan.supplier_id
                         when operationplan.type = 'DO' then 'Ship '||operationplan.item_id||' from '||operationplan.origin_id||' to '||operationplan.destination_id
                    else operationplan.operation_id end,
                    operationplan.status,
                    operationplan.item_id,
                    coalesce(operationplan.location_id, operationplan.destination_id),
                    case when operationplan.type = 'STCK' then '' else to_char(operationplan.startdate,'YYYY-MM-DD hh24:mi:ss') end,
                    case when operationplan.type = 'STCK' then '' else to_char(operationplan.enddate,'YYYY-MM-DD hh24:mi:ss') end,
                    trim(trailing '.' from (trim(trailing '0' from round(cte.quantity,8)::text)))||'/'||
                    trim(trailing '.' from (trim(trailing '0' from round(operationplan.quantity,8)::text)))
                    from cte
                    inner join operationplan on operationplan.reference = cte.reference
                    order by cte.rownum
                    """,
                    (opplan.reference,),
                )

                if cursor.rowcount > 0:
                    res["upstreamoperationplans"] = []
                    for a in cursor.fetchall():
                        res["upstreamoperationplans"].append(
                            [
                                a[0],  # level
                                a[1],  # reference
                                a[2],  # type
                                a[3] or "",  # operation (null if optype is STCK)
                                a[4],  # status
                                a[5],  # item
                                a[6],  # location
                                a[7],  # startdate
                                a[8],  # enddate
                                a[9],  # quantity,
                                0 if a[0] == 1 else 2,
                            ]
                        )

                # Final result
                if first:
                    yield "[%s" % json.dumps(res)
                    first = False
                else:
                    yield ",%s" % json.dumps(res)
                yield "]"
            except Exception as e:
                # Ignore exceptions and move on
                logger.error("Error retrieving operationplan: %s" % e)

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    @method_decorator(staff_member_required)
    def get(self, request):
        # Only accept ajax requests on this URL
        if not request.is_ajax():
            raise Http404("Only ajax requests allowed")

        # Stream back the response
        response = StreamingHttpResponse(
            content_type="application/json; charset=%s" % settings.DEFAULT_CHARSET,
            streaming_content=self.getData(request),
        )
        response["Cache-Control"] = "no-cache, no-store"
        return response

    @method_decorator(staff_member_required)
    def post(self, request):
        # Only accept ajax requests on this URL
        if not request.is_ajax():
            raise Http404("Only ajax requests allowed")

        # Parse the posted data
        try:
            data = json.JSONDecoder().decode(
                request.read().decode(request.encoding or settings.DEFAULT_CHARSET)
            )
        except Exception as e:
            logger.error("Error updating operationplan data: %s" % e)
            return HttpResponseServerError(
                "Error updating operationplan data", content_type="text/html"
            )

        update_PO = request.user.has_perm("input.change_purchaseorder")
        update_MO = request.user.has_perm("input.change_manufacturingorder")
        update_DO = request.user.has_perm("input.change_distributionorder")

        for opplan_data in data:
            try:
                # Read the object from the database
                opplan = (
                    OperationPlan.objects.all()
                    .using(request.database)
                    .get(reference=opplan_data.get("id", None))
                )

                # Check permissions
                if opplan.type == "DO" and not update_DO:
                    continue
                if opplan.type == "PO" and not update_PO:
                    continue
                if opplan.type == "MO" and not update_MO:
                    continue

                # Update fields
                save = False
                if "start" in opplan_data:
                    # Update start date
                    opplan.startdate = datetime.strptime(
                        opplan_data["start"], "%Y-%m-%dT%H:%M:%S"
                    )
                    save = True
                if "end" in opplan_data:
                    # Update end date
                    opplan.enddate = datetime.strptime(
                        opplan_data["end"], "%Y-%m-%dT%H:%M:%S"
                    )
                    save = True
                if "quantity" in opplan_data:
                    # Update quantity
                    opplan.quantity = opplan_data["quantity"]
                    save = True
                if "quantity_completed" in opplan_data:
                    # Update quantity
                    opplan.quantity_completed = opplan_data["quantity_completed"]
                    save = True
                if "status" in opplan_data:
                    # Status quantity
                    opplan.status = opplan_data["status"]
                    save = True
                if "reference" in opplan_data:
                    # Update reference
                    opplan.reference = opplan_data["reference"]
                    save = True

                # Save if changed
                if save:
                    opplan.save(
                        using=request.database,
                        update_fields=[
                            "startdate",
                            "enddate",
                            "quantity",
                            "quantity_completed",
                            "reference",
                            "lastmodified",
                        ],
                    )
            except OperationPlan.DoesNotExist:
                # Silently ignore
                pass
            except Exception as e:
                # Swallow the exception and move on
                logger.error("Error updating operationplan: %s" % e)
        return HttpResponse(content="OK")
