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
from datetime import timedelta, datetime

from django.db import connections, transaction
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.utils.encoding import force_text
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from freppledb.boot import getAttributeFields
from freppledb.input.models import Buffer, Item, Location, OperationPlanMaterial
from freppledb.common.report import (
    GridPivot,
    GridFieldText,
    GridFieldNumber,
    GridFieldInteger,
    GridFieldLastModified,
    GridFieldCurrency,
)


class OverviewReport(GridPivot):
    """
    A report showing the inventory profile of buffers.
    """

    template = "output/buffer.html"
    title = _("Inventory report")
    new_arg_logic = True

    @classmethod
    def basequeryset(reportclass, request, *args, **kwargs):
        if hasattr(request, "basequeryset"):
            return request.basequeryset

        item = None
        location = None
        batch = None

        if len(args) and args[0]:
            if request.path_info.startswith(
                "/buffer/item/"
            ) or request.path_info.startswith("/detail/input/item/"):
                item = args[0]
            else:
                i_b_l = args[0].split(" @ ")
                if len(i_b_l) == 1:
                    b = Buffer.objects.values("item", "location").get(id=args[0])
                    item = b["item"]
                    location = b["location"]
                elif len(i_b_l) == 2:
                    item = i_b_l[0]
                    location = i_b_l[1]
                else:
                    item = i_b_l[0]
                    location = i_b_l[2]
                    batch = i_b_l[1]

        request.basequeryset = OperationPlanMaterial.objects.values(
            "item", "location", "item__type"
        ).filter(
            ((Q(item__type="make to stock") | Q(item__type__isnull=True)))
            | (Q(item__type="make to order") & Q(operationplan__batch__isnull=False))
        )

        if item:
            request.basequeryset = request.basequeryset.filter(item=item)

        if location:
            request.basequeryset = request.basequeryset.filter(location=location)

        if batch:
            request.basequeryset = request.basequeryset.filter(
                operationplan__batch=batch
            )

        request.basequeryset = request.basequeryset.annotate(
            buffer=RawSQL(
                "operationplanmaterial.item_id || "
                "(case when item.type is distinct from 'make to order' then '' else ' @ ' || operationplan.batch end) "
                "|| ' @ ' || operationplanmaterial.location_id",
                (),
            ),
            opplan_batch=RawSQL(
                "case when item.type is distinct from 'make to order' then '' else operationplan.batch end",
                (),
            ),
        ).distinct()

        return request.basequeryset

    model = OperationPlanMaterial
    default_sort = (1, "asc", 2, "asc")
    permissions = (("view_inventory_report", "Can view inventory report"),)
    help_url = "user-interface/plan-analysis/inventory-report.html"

    rows = (
        GridFieldText(
            "buffer", title=_("buffer"), editable=False, key=True, initially_hidden=True
        ),
        GridFieldText(
            "item",
            title=_("item"),
            editable=False,
            field_name="item__name",
            formatter="detail",
            extra='"role":"input/item"',
        ),
        GridFieldText(
            "location",
            title=_("location"),
            editable=False,
            field_name="location__name",
            formatter="detail",
            extra='"role":"input/location"',
        ),
        # Optional fields referencing the item
        GridFieldText(
            "item__description",
            title=format_lazy("{} - {}", _("item"), _("description")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "item__type",
            title=format_lazy("{} - {}", _("item"), _("type")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "item__category",
            title=format_lazy("{} - {}", _("item"), _("category")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "item__subcategory",
            title=format_lazy("{} - {}", _("item"), _("subcategory")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldCurrency(
            "item__cost",
            title=format_lazy("{} - {}", _("item"), _("cost")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldNumber(
            "item__volume",
            title=format_lazy("{} - {}", _("item"), _("volume")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldNumber(
            "item__weight",
            title=format_lazy("{} - {}", _("item"), _("weight")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldInteger(
            "item__periodofcover",
            title=format_lazy("{} - {}", _("item"), _("period of cover")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "item__owner",
            title=format_lazy("{} - {}", _("item"), _("owner")),
            field_name="item__owner__name",
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "item__source",
            title=format_lazy("{} - {}", _("item"), _("source")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldLastModified(
            "item__lastmodified",
            title=format_lazy("{} - {}", _("item"), _("last modified")),
            initially_hidden=True,
            editable=False,
        ),
        # Optional fields referencing the location
        GridFieldText(
            "location__description",
            title=format_lazy("{} - {}", _("location"), _("description")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "location__category",
            title=format_lazy("{} - {}", _("location"), _("category")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "location__subcategory",
            title=format_lazy("{} - {}", _("location"), _("subcategory")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "location__available",
            title=format_lazy("{} - {}", _("location"), _("available")),
            initially_hidden=True,
            field_name="location__available__name",
            formatter="detail",
            extra='"role":"input/calendar"',
            editable=False,
        ),
        GridFieldText(
            "location__owner",
            title=format_lazy("{} - {}", _("location"), _("owner")),
            initially_hidden=True,
            field_name="location__owner__name",
            formatter="detail",
            extra='"role":"input/location"',
            editable=False,
        ),
        GridFieldText(
            "location__source",
            title=format_lazy("{} - {}", _("location"), _("source")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldLastModified(
            "location__lastmodified",
            title=format_lazy("{} - {}", _("location"), _("last modified")),
            initially_hidden=True,
            editable=False,
        ),
        GridFieldText(
            "batch",
            title=_("batch"),
            field_name="opplan_batch",
            editable=False,
            initially_hidden=True,
        ),
    )

    crosses = (
        ("startoh", {"title": _("start inventory")}),
        (
            "startohdoc",
            {"title": _("start inventory days of cover"), "initially_hidden": True},
        ),
        ("safetystock", {"title": _("safety stock")}),
        ("consumed", {"title": _("total consumed")}),
        ("consumedMO", {"title": _("consumed by MO"), "initially_hidden": True}),
        ("consumedDO", {"title": _("consumed by DO"), "initially_hidden": True}),
        ("consumedSO", {"title": _("consumed by SO"), "initially_hidden": True}),
        ("produced", {"title": _("total produced")}),
        ("producedMO", {"title": _("produced by MO"), "initially_hidden": True}),
        ("producedDO", {"title": _("produced by DO"), "initially_hidden": True}),
        ("producedPO", {"title": _("produced by PO"), "initially_hidden": True}),
        ("endoh", {"title": _("end inventory")}),
        (
            "total_in_progress",
            {"title": _("total in progress"), "initially_hidden": True},
        ),
        (
            "work_in_progress_mo",
            {"title": _("work in progress MO"), "initially_hidden": True},
        ),
        ("on_order_po", {"title": _("on order PO"), "initially_hidden": True}),
        ("in_transit_do", {"title": _("in transit DO"), "initially_hidden": True}),
    )

    @classmethod
    def initialize(reportclass, request):
        if reportclass._attributes_added != 2:
            reportclass._attributes_added = 2
            reportclass.attr_sql = ""
            # Adding custom item attributes
            for f in getAttributeFields(
                Item, related_name_prefix="item", initially_hidden=True
            ):
                reportclass.rows += (f,)
                reportclass.attr_sql += "item.%s, " % f.name.split("__")[-1]
            # Adding custom location attributes
            for f in getAttributeFields(
                Location, related_name_prefix="location", initially_hidden=True
            ):
                reportclass.rows += (f,)
                reportclass.attr_sql += "location.%s, " % f.name.split("__")[-1]

    @classmethod
    def extra_context(reportclass, request, *args, **kwargs):
        if not hasattr(request, "basequeryset"):
            reportclass.basequeryset(request, *args, **kwargs)
        if args and args[0]:
            if request.path_info.startswith(
                "/buffer/item/"
            ) or request.path_info.startswith("/detail/input/item/"):
                request.session["lasttab"] = "inventory"
                r = {
                    "title": force_text(Item._meta.verbose_name) + " " + args[0],
                    "post_title": _("inventory"),
                    "active_tab": "inventory",
                    "model": Item,
                }
                if request.basequeryset.using(request.database).count() <= 1:
                    r["args"] = args
                    r["mode"] = "table"
                else:
                    r["args"] = None
                return r
            else:
                request.session["lasttab"] = "plan"
                index = args[0].find(" @ ")
                if index == -1:
                    buffer = Buffer.objects.get(id=args[0])
                return {
                    "title": force_text(Buffer._meta.verbose_name)
                    + " "
                    + (
                        args[0]
                        if index != -1
                        else buffer.item.name + " @ " + buffer.location.name
                    ),
                    "post_title": _("plan"),
                    "active_tab": "plan",
                    "mode": "table",
                    "model": Buffer,
                }
        else:
            return {}

    @classmethod
    def query(reportclass, request, basequery, sortsql="1 asc"):
        basesql, baseparams = basequery.query.get_compiler(basequery.db).as_sql(
            with_col_aliases=False
        )

        # Execute the actual query
        query = """
           select
           opplanmat.buffer,
           item.name item_id,
           location.name location_id,
           item.description,
           item.type,
           item.category,
           item.subcategory,
           item.cost,
           item.volume,
           item.weight,
           item.periodofcover,
           item.owner_id,
           item.source,
           item.lastmodified,
           location.description,
           location.category,
           location.subcategory,
           location.available_id,
           location.owner_id,
           location.source,
           location.lastmodified,
           opplanmat.opplan_batch,
           %s
           case
             when d.history then jsonb_build_object(
               'onhand', min(ax_buffer.onhand)
               )
           else (
             select jsonb_build_object(
               'onhand', onhand,
               'flowdate', to_char(flowdate,'YYYY-MM-DD HH24:MI:SS'),
               'periodofcover', periodofcover
               )
             from operationplanmaterial
             inner join operationplan
               on operationplanmaterial.operationplan_id = operationplan.reference
             where operationplanmaterial.item_id = item.name
               and operationplanmaterial.location_id = location.name
               and (item.type is distinct from 'make to order' or operationplan.batch is not distinct from opplanmat.opplan_batch)
               and flowdate < greatest(d.startdate,%%s)
             order by flowdate desc, id desc limit 1
             )
           end as startoh,
           d.bucket,
           d.startdate,
           d.enddate,
           d.history,
           case when d.history then min(ax_buffer.safetystock)
           else
           (select safetystock from
            (
            select 1 as priority, coalesce(
              (select value from calendarbucket
               where calendar_id = 'SS for ' || opplanmat.buffer
               and greatest(d.startdate,%%s) >= startdate and greatest(d.startdate,%%s) < enddate
               order by priority limit 1),
              (select defaultvalue from calendar where name = 'SS for ' || opplanmat.buffer)
              ) as safetystock
            union all
            select 2 as priority, coalesce(
              (select value
               from calendarbucket
               where calendar_id = (
                 select minimum_calendar_id
                 from buffer
                 where item_id = item.name
                 and location_id = location.name
                 and (item.type is distinct from 'make to order' or buffer.batch is not distinct from opplanmat.opplan_batch)
                 )
               and greatest(d.startdate,%%s) >= startdate
               and greatest(d.startdate,%%s) < enddate
               order by priority limit 1),
              (select defaultvalue
               from calendar
               where name = (
                 select minimum_calendar_id
                 from buffer
                 where item_id = item.name
                 and location_id = location.name
                 and (item.type is distinct from 'make to order' or buffer.batch is not distinct from opplanmat.opplan_batch)
                 )
              )
            ) as safetystock
            union all
            select 3 as priority, minimum as safetystock
            from buffer
            where item_id = item.name
            and location_id = location.name
            and (item.type is distinct from 'make to order' or buffer.batch is not distinct from opplanmat.opplan_batch)
            ) t
            where t.safetystock is not null
            order by priority
            limit 1)
            end as safetystock,
            case when d.history then jsonb_build_object()
            else (
             select jsonb_build_object(
               'work_in_progress_mo', sum(case when (startdate < d.enddate and enddate >= d.enddate) and opm.quantity > 0 and operationplan.type = 'MO' then opm.quantity else 0 end),
               'on_order_po', sum(case when (startdate < d.enddate and enddate >= d.enddate) and opm.quantity > 0 and operationplan.type = 'PO' then opm.quantity else 0 end),
               'in_transit_do', sum(case when (startdate < d.enddate and enddate >= d.enddate) and opm.quantity > 0 and operationplan.type = 'DO' then opm.quantity else 0 end),
               'total_in_progress', sum(case when (startdate < d.enddate and enddate >= d.enddate) and opm.quantity > 0 then opm.quantity else 0 end),
               'consumed', sum(case when (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity < 0 then -opm.quantity else 0 end),
               'consumedMO', sum(case when operationplan.type = 'MO' and (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity < 0 then -opm.quantity else 0 end),
               'consumedDO', sum(case when operationplan.type = 'DO' and (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity < 0 then -opm.quantity else 0 end),
               'consumedSO', sum(case when operationplan.type = 'DLVR' and (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity < 0 then -opm.quantity else 0 end),
               'produced', sum(case when (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity > 0 then opm.quantity else 0 end),
               'producedMO', sum(case when operationplan.type = 'MO' and (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity > 0 then opm.quantity else 0 end),
               'producedDO', sum(case when operationplan.type = 'DO' and (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity > 0 then opm.quantity else 0 end),
               'producedPO', sum(case when operationplan.type = 'PO' and (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate) and opm.quantity > 0 then opm.quantity else 0 end)
               )
             from operationplanmaterial opm
             inner join operationplan
             on operationplan.reference = opm.operationplan_id
               and ((startdate < d.enddate and enddate >= d.enddate)
               or (opm.flowdate >= greatest(d.startdate,%%s) and opm.flowdate < d.enddate))
             where opm.item_id = item.name
               and opm.location_id = location.name
               and (item.type is distinct from 'make to order' or operationplan.batch is not distinct from opplanmat.opplan_batch)
             )
           end as ongoing
           from
           (%s) opplanmat
           inner join item on item.name = opplanmat.item_id
           inner join location on location.name = opplanmat.location_id
           -- Multiply with buckets
           cross join (
             select name as bucket, startdate, enddate,
               min(snapshot_date) as snapshot_date,
               enddate < %%s as history
             from common_bucketdetail
             left outer join ax_manager
               on snapshot_date >= common_bucketdetail.startdate
               and snapshot_date < common_bucketdetail.enddate
             where common_bucketdetail.bucket_id = %%s
               and common_bucketdetail.enddate > %%s
               and common_bucketdetail.startdate < %%s
             group by common_bucketdetail.name, common_bucketdetail.startdate, common_bucketdetail.enddate
             ) d
           -- join with the archive data
           left outer join ax_buffer
             on ax_buffer.snapshot_date_id = d.snapshot_date
             and ax_buffer.item =  opplanmat.item_id
             and ax_buffer.location =  opplanmat.location_id
             and (ax_buffer.batch = opplanmat.opplan_batch or ax_buffer.batch is null)
          group by
           opplanmat.buffer,
           item.name,
           location.name,
           item.description,
           item.type,
           item.category,
           item.subcategory,
           item.cost,
           item.volume,
           item.weight,
           item.periodofcover,
           item.owner_id,
           item.source,
           item.lastmodified,
           location.description,
           location.category,
           location.subcategory,
           location.available_id,
           location.owner_id,
           location.source,
           location.lastmodified,
           opplanmat.opplan_batch,
           d.bucket,
           d.startdate,
           d.enddate,
           d.history
           order by %s, d.startdate
        """ % (
            reportclass.attr_sql,
            basesql,
            sortsql,
        )

        # Build the python result
        with transaction.atomic(using=request.database):
            with connections[request.database].chunked_cursor() as cursor_chunked:
                cursor_chunked.execute(
                    query,
                    (
                        request.report_startdate,  # startoh
                        request.report_startdate,
                        request.report_startdate,
                        request.report_startdate,
                        request.report_startdate,  # safetystock
                    )
                    + (request.report_startdate,) * 9
                    + baseparams  # ongoing
                    + (  # opplanmat
                        request.current_date,
                        request.report_bucket,
                        request.report_startdate,
                        request.report_enddate,
                    ),  # bucket d
                )
                itemattributefields = getAttributeFields(
                    Item, related_name_prefix="item"
                )
                locationattributefields = getAttributeFields(
                    Location, related_name_prefix="location"
                )
                for row in cursor_chunked:
                    numfields = len(row)
                    history = row[numfields - 3]
                    res = {
                        "buffer": row[0],
                        "item": row[1],
                        "location": row[2],
                        "item__description": row[3],
                        "item__type": row[4],
                        "item__category": row[5],
                        "item__subcategory": row[6],
                        "item__cost": row[7],
                        "item__volume": row[8],
                        "item__weight": row[9],
                        "item__periodofcover": row[10],
                        "item__owner": row[11],
                        "item__source": row[12],
                        "item__lastmodified": row[13],
                        "location__description": row[14],
                        "location__category": row[15],
                        "location__subcategory": row[16],
                        "location__available": row[17],
                        "location__owner": row[18],
                        "location__source": row[19],
                        "location__lastmodified": row[20],
                        "batch": row[21],
                        "startoh": row[numfields - 7]["onhand"]
                        if row[numfields - 7]
                        else 0,
                        "startohdoc": None
                        if history
                        else max(
                            0,
                            0
                            if (
                                row[numfields - 7]["onhand"]
                                if row[numfields - 7]
                                else 0
                            )
                            <= 0
                            else (
                                999
                                if row[numfields - 7]["periodofcover"] == 86313600
                                else (
                                    datetime.strptime(
                                        row[numfields - 7]["flowdate"],
                                        "%Y-%m-%d %H:%M:%S",
                                    )
                                    + timedelta(
                                        seconds=row[numfields - 7]["periodofcover"]
                                    )
                                    - row[numfields - 5]
                                ).days
                                if row[numfields - 7]["periodofcover"]
                                else 999
                            ),
                        ),
                        "bucket": row[numfields - 6],
                        "startdate": row[numfields - 5],
                        "enddate": row[numfields - 4],
                        "history": history,
                        "safetystock": row[numfields - 2]
                        if history
                        else row[numfields - 2] or 0,
                        "consumed": None
                        if history
                        else row[numfields - 1]["consumed"] or 0,
                        "consumedMO": None
                        if history
                        else row[numfields - 1]["consumedMO"] or 0,
                        "consumedDO": None
                        if history
                        else row[numfields - 1]["consumedDO"] or 0,
                        "consumedSO": None
                        if history
                        else row[numfields - 1]["consumedSO"] or 0,
                        "produced": None
                        if history
                        else row[numfields - 1]["produced"] or 0,
                        "producedMO": None
                        if history
                        else row[numfields - 1]["producedMO"] or 0,
                        "producedDO": None
                        if history
                        else row[numfields - 1]["producedDO"] or 0,
                        "producedPO": None
                        if history
                        else row[numfields - 1]["producedPO"] or 0,
                        "total_in_progress": None
                        if history
                        else row[numfields - 1]["total_in_progress"] or 0,
                        "work_in_progress_mo": None
                        if history
                        else row[numfields - 1]["work_in_progress_mo"] or 0,
                        "on_order_po": None
                        if history
                        else row[numfields - 1]["on_order_po"] or 0,
                        "in_transit_do": None
                        if history
                        else row[numfields - 1]["in_transit_do"] or 0,
                        "endoh": None
                        if history
                        else (
                            float(
                                row[numfields - 7]["onhand"]
                                if row[numfields - 7]
                                else 0
                            )
                            + float(row[numfields - 1]["produced"] or 0)
                            - float(row[numfields - 1]["consumed"] or 0)
                        ),
                    }

                    # Add attribute fields
                    idx = 22
                    for f in itemattributefields:
                        res[f.field_name] = row[idx]
                        idx += 1
                    for f in locationattributefields:
                        res[f.field_name] = row[idx]
                        idx += 1
                    yield res
