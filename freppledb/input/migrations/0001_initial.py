#
# Copyright (C) 2015 by frePPLe bvba
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
import datetime

from django.core.management import call_command
from django.db import models, migrations
import django.utils.timezone

import freppledb.common.fields


def loadParameters(apps, schema_editor):
    call_command(
        "loaddata",
        "parameters.json",
        app_label="input",
        verbosity=0,
        database=schema_editor.connection.alias,
    )


class Migration(migrations.Migration):

    dependencies = [("common", "0001_initial"), ("admin", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Buffer",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        verbose_name="type",
                        null=True,
                        default="default",
                        choices=[
                            ("default", "Default"),
                            ("infinite", "Infinite"),
                            ("procure", "Procure"),
                        ],
                        blank=True,
                        max_length=20,
                    ),
                ),
                (
                    "onhand",
                    models.DecimalField(
                        verbose_name="onhand",
                        null=True,
                        default="0.00",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="current inventory",
                    ),
                ),
                (
                    "minimum",
                    models.DecimalField(
                        verbose_name="minimum",
                        null=True,
                        default="0.00",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Safety stock",
                    ),
                ),
                (
                    "leadtime",
                    freppledb.common.fields.DurationField(
                        verbose_name="leadtime",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Leadtime for supplier of a procure buffer",
                    ),
                ),
                (
                    "fence",
                    freppledb.common.fields.DurationField(
                        verbose_name="fence",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Frozen fence for creating new procurements",
                    ),
                ),
                (
                    "min_inventory",
                    models.DecimalField(
                        verbose_name="min_inventory",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Inventory level that triggers replenishment of a procure buffer",
                    ),
                ),
                (
                    "max_inventory",
                    models.DecimalField(
                        verbose_name="max_inventory",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Inventory level to which a procure buffer is replenished",
                    ),
                ),
                (
                    "min_interval",
                    freppledb.common.fields.DurationField(
                        verbose_name="min_interval",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Minimum time interval between replenishments of a procure buffer",
                    ),
                ),
                (
                    "max_interval",
                    freppledb.common.fields.DurationField(
                        verbose_name="max_interval",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Maximum time interval between replenishments of a procure buffer",
                    ),
                ),
                (
                    "size_minimum",
                    models.DecimalField(
                        verbose_name="size_minimum",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Minimum size of replenishments of a procure buffer",
                    ),
                ),
                (
                    "size_multiple",
                    models.DecimalField(
                        verbose_name="size_multiple",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Replenishments of a procure buffer are a multiple of this quantity",
                    ),
                ),
                (
                    "size_maximum",
                    models.DecimalField(
                        verbose_name="size_maximum",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Maximum size of replenishments of a procure buffer",
                    ),
                ),
            ],
            options={
                "db_table": "buffer",
                "ordering": ["name"],
                "verbose_name_plural": "buffers",
                "verbose_name": "buffer",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Calendar",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "defaultvalue",
                    models.DecimalField(
                        verbose_name="default value",
                        null=True,
                        default="0.00",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Value to be used when no entry is effective",
                    ),
                ),
            ],
            options={
                "db_table": "calendar",
                "ordering": ["name"],
                "verbose_name_plural": "calendars",
                "verbose_name": "calendar",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="CalendarBucket",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "startdate",
                    models.DateTimeField(
                        null=True, verbose_name="start date", blank=True
                    ),
                ),
                (
                    "enddate",
                    models.DateTimeField(
                        null=True,
                        blank=True,
                        verbose_name="end date",
                        default=datetime.datetime(2030, 12, 31, 0, 0),
                    ),
                ),
                (
                    "value",
                    models.DecimalField(
                        blank=True,
                        max_digits=15,
                        verbose_name="value",
                        default="0.00",
                        decimal_places=4,
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        null=True, blank=True, verbose_name="priority", default=0
                    ),
                ),
                ("monday", models.BooleanField(verbose_name="Monday", default=True)),
                ("tuesday", models.BooleanField(verbose_name="Tuesday", default=True)),
                (
                    "wednesday",
                    models.BooleanField(verbose_name="Wednesday", default=True),
                ),
                (
                    "thursday",
                    models.BooleanField(verbose_name="Thursday", default=True),
                ),
                ("friday", models.BooleanField(verbose_name="Friday", default=True)),
                (
                    "saturday",
                    models.BooleanField(verbose_name="Saturday", default=True),
                ),
                ("sunday", models.BooleanField(verbose_name="Sunday", default=True)),
                (
                    "starttime",
                    models.TimeField(
                        null=True,
                        blank=True,
                        verbose_name="start time",
                        default=datetime.time(0, 0),
                    ),
                ),
                (
                    "endtime",
                    models.TimeField(
                        null=True,
                        blank=True,
                        verbose_name="end time",
                        default=datetime.time(23, 59, 59),
                    ),
                ),
                (
                    "calendar",
                    models.ForeignKey(
                        related_name="buckets",
                        verbose_name="calendar",
                        to="input.Calendar",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "calendarbucket",
                "ordering": ["calendar", "id"],
                "verbose_name_plural": "calendar buckets",
                "verbose_name": "calendar bucket",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Customer",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        verbose_name="owner",
                        related_name="xchildren",
                        null=True,
                        blank=True,
                        to="input.Customer",
                        help_text="Hierarchical parent",
                        on_delete=models.SET_NULL,
                    ),
                ),
            ],
            options={
                "db_table": "customer",
                "ordering": ["name"],
                "verbose_name_plural": "customers",
                "verbose_name": "customer",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Demand",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "due",
                    models.DateTimeField(
                        verbose_name="due", help_text="Due date of the demand"
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        verbose_name="status",
                        null=True,
                        default="open",
                        max_length=10,
                        choices=[
                            ("inquiry", "Inquiry"),
                            ("quote", "Quote"),
                            ("open", "Open"),
                            ("closed", "Closed"),
                            ("canceled", "Canceled"),
                        ],
                        blank=True,
                        help_text='Status of the demand. Only "open" demands are planned',
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        verbose_name="quantity", max_digits=15, decimal_places=4
                    ),
                ),
                (
                    "priority",
                    models.PositiveIntegerField(
                        choices=[
                            (1, "1"),
                            (2, "2"),
                            (3, "3"),
                            (4, "4"),
                            (5, "5"),
                            (6, "6"),
                            (7, "7"),
                            (8, "8"),
                            (9, "9"),
                            (10, "10"),
                            (11, "11"),
                            (12, "12"),
                            (13, "13"),
                            (14, "14"),
                            (15, "15"),
                            (16, "16"),
                            (17, "17"),
                            (18, "18"),
                            (19, "19"),
                            (20, "20"),
                        ],
                        verbose_name="priority",
                        default=10,
                        help_text="Priority of the demand (lower numbers indicate more important demands)",
                    ),
                ),
                (
                    "minshipment",
                    models.DecimalField(
                        verbose_name="minimum shipment",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Minimum shipment quantity when planning this demand",
                    ),
                ),
                (
                    "maxlateness",
                    freppledb.common.fields.DurationField(
                        verbose_name="maximum lateness",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Maximum lateness allowed when planning this demand",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        verbose_name="customer",
                        null=True,
                        blank=True,
                        to="input.Customer",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "demand",
                "ordering": ["name"],
                "verbose_name_plural": "sales orders",
                "verbose_name": "sales order",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="DistributionOrder",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.IntegerField(
                        primary_key=True,
                        verbose_name="identifier",
                        serialize=False,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "reference",
                    models.CharField(
                        null=True,
                        verbose_name="reference",
                        blank=True,
                        max_length=300,
                        help_text="External reference of this order",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        verbose_name="status",
                        help_text="Status of the order",
                        max_length=20,
                        null=True,
                        choices=[
                            ("proposed", "proposed"),
                            ("confirmed", "confirmed"),
                            ("closed", "closed"),
                        ],
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=15,
                        verbose_name="quantity",
                        default="1.00",
                        decimal_places=4,
                    ),
                ),
                (
                    "startdate",
                    models.DateTimeField(
                        null=True,
                        verbose_name="start date",
                        blank=True,
                        help_text="start date",
                    ),
                ),
                (
                    "enddate",
                    models.DateTimeField(
                        null=True,
                        verbose_name="end date",
                        blank=True,
                        help_text="end date",
                    ),
                ),
                (
                    "consume_material",
                    models.BooleanField(
                        verbose_name="consume material",
                        default=True,
                        help_text="Consume material at origin location",
                    ),
                ),
                (
                    "criticality",
                    models.DecimalField(
                        null=True,
                        max_digits=15,
                        verbose_name="criticality",
                        blank=True,
                        decimal_places=4,
                    ),
                ),
            ],
            options={
                "db_table": "distribution_order",
                "ordering": ["id"],
                "verbose_name_plural": "distribution orders",
                "verbose_name": "distribution order",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Flow",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=15,
                        verbose_name="quantity",
                        default="1.00",
                        decimal_places=4,
                        help_text="Quantity to consume or produce per operationplan unit",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        verbose_name="type",
                        null=True,
                        default="start",
                        max_length=20,
                        choices=[
                            ("start", "Start"),
                            ("end", "End"),
                            ("fixed_start", "Fixed start"),
                            ("fixed_end", "Fixed end"),
                        ],
                        blank=True,
                        help_text="Consume/produce material at the start or the end of the operationplan",
                    ),
                ),
                (
                    "effective_start",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective start",
                        blank=True,
                        help_text="Validity start date",
                    ),
                ),
                (
                    "effective_end",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective end",
                        blank=True,
                        help_text="Validity end date",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        null=True,
                        verbose_name="name",
                        blank=True,
                        max_length=300,
                        help_text="Optional name of this flow",
                    ),
                ),
                (
                    "alternate",
                    models.CharField(
                        null=True,
                        verbose_name="alternate",
                        blank=True,
                        max_length=300,
                        help_text="Puts the flow in a group of alternate flows",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        verbose_name="priority",
                        default=1,
                        help_text="Priority of this flow in a group of alternates",
                    ),
                ),
                (
                    "search",
                    models.CharField(
                        verbose_name="search mode",
                        null=True,
                        max_length=20,
                        choices=[
                            ("PRIORITY", "priority"),
                            ("MINCOST", "minimum cost"),
                            ("MINPENALTY", "minimum penalty"),
                            ("MINCOSTPENALTY", "minimum cost plus penalty"),
                        ],
                        blank=True,
                        help_text="Method to select preferred alternate",
                    ),
                ),
            ],
            options={
                "db_table": "flow",
                "verbose_name": "flow",
                "verbose_name_plural": "flows",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Item",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        verbose_name="price",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Selling price of the item",
                    ),
                ),
            ],
            options={
                "db_table": "item",
                "ordering": ["name"],
                "verbose_name_plural": "items",
                "verbose_name": "item",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ItemDistribution",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "leadtime",
                    freppledb.common.fields.DurationField(
                        verbose_name="lead time",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Shipping lead time",
                    ),
                ),
                (
                    "sizeminimum",
                    models.DecimalField(
                        verbose_name="size minimum",
                        null=True,
                        default="1.0",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A minimum shipping quantity",
                    ),
                ),
                (
                    "sizemultiple",
                    models.DecimalField(
                        verbose_name="size multiple",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A multiple shipping quantity",
                    ),
                ),
                (
                    "cost",
                    models.DecimalField(
                        verbose_name="cost",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Shipping cost per unit",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        verbose_name="priority",
                        default=1,
                        help_text="Priority among all alternates",
                    ),
                ),
                (
                    "effective_start",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective start",
                        blank=True,
                        help_text="Validity start date",
                    ),
                ),
                (
                    "effective_end",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective end",
                        blank=True,
                        help_text="Validity end date",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        related_name="distributions",
                        verbose_name="item",
                        to="input.Item",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "itemdistribution",
                "verbose_name": "item distribution",
                "verbose_name_plural": "item distributions",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ItemSupplier",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "leadtime",
                    freppledb.common.fields.DurationField(
                        verbose_name="lead time",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Purchasing lead time",
                    ),
                ),
                (
                    "sizeminimum",
                    models.DecimalField(
                        verbose_name="size minimum",
                        null=True,
                        default="1.0",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A minimum purchasing quantity",
                    ),
                ),
                (
                    "sizemultiple",
                    models.DecimalField(
                        verbose_name="size multiple",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A multiple purchasing quantity",
                    ),
                ),
                (
                    "cost",
                    models.DecimalField(
                        verbose_name="cost",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Purchasing cost per unit",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        verbose_name="priority",
                        default=1,
                        help_text="Priority among all alternates",
                    ),
                ),
                (
                    "effective_start",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective start",
                        blank=True,
                        help_text="Validity start date",
                    ),
                ),
                (
                    "effective_end",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective end",
                        blank=True,
                        help_text="Validity end date",
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        related_name="itemsuppliers",
                        verbose_name="item",
                        to="input.Item",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "itemsupplier",
                "verbose_name": "item supplier",
                "verbose_name_plural": "item suppliers",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Load",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=15,
                        verbose_name="quantity",
                        default="1.00",
                        decimal_places=4,
                    ),
                ),
                (
                    "effective_start",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective start",
                        blank=True,
                        help_text="Validity start date",
                    ),
                ),
                (
                    "effective_end",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective end",
                        blank=True,
                        help_text="Validity end date",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        null=True,
                        verbose_name="name",
                        blank=True,
                        max_length=300,
                        help_text="Optional name of this load",
                    ),
                ),
                (
                    "alternate",
                    models.CharField(
                        null=True,
                        verbose_name="alternate",
                        blank=True,
                        max_length=300,
                        help_text="Puts the load in a group of alternate loads",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        verbose_name="priority",
                        default=1,
                        help_text="Priority of this load in a group of alternates",
                    ),
                ),
                (
                    "setup",
                    models.CharField(
                        null=True,
                        verbose_name="setup",
                        blank=True,
                        max_length=300,
                        help_text="Setup required on the resource for this operation",
                    ),
                ),
                (
                    "search",
                    models.CharField(
                        verbose_name="search mode",
                        null=True,
                        max_length=20,
                        choices=[
                            ("PRIORITY", "priority"),
                            ("MINCOST", "minimum cost"),
                            ("MINPENALTY", "minimum penalty"),
                            ("MINCOSTPENALTY", "minimum cost plus penalty"),
                        ],
                        blank=True,
                        help_text="Method to select preferred alternate",
                    ),
                ),
            ],
            options={
                "db_table": "resourceload",
                "verbose_name": "load",
                "verbose_name_plural": "loads",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "available",
                    models.ForeignKey(
                        verbose_name="available",
                        null=True,
                        blank=True,
                        to="input.Calendar",
                        help_text="Calendar defining the working hours and holidays of this location",
                        on_delete=models.SET_NULL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        verbose_name="owner",
                        related_name="xchildren",
                        null=True,
                        blank=True,
                        to="input.Location",
                        help_text="Hierarchical parent",
                        on_delete=models.SET_NULL,
                    ),
                ),
            ],
            options={
                "db_table": "location",
                "ordering": ["name"],
                "verbose_name_plural": "locations",
                "verbose_name": "location",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Operation",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        verbose_name="type",
                        null=True,
                        default="fixed_time",
                        choices=[
                            ("fixed_time", "fixed_time"),
                            ("time_per", "time_per"),
                            ("routing", "routing"),
                            ("alternate", "alternate"),
                            ("split", "split"),
                        ],
                        blank=True,
                        max_length=20,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "fence",
                    freppledb.common.fields.DurationField(
                        verbose_name="release fence",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Operationplans within this time window from the current day are expected to be released to production ERP",
                    ),
                ),
                (
                    "posttime",
                    freppledb.common.fields.DurationField(
                        verbose_name="post-op time",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A delay time to be respected as a soft constraint after ending the operation",
                    ),
                ),
                (
                    "sizeminimum",
                    models.DecimalField(
                        verbose_name="size minimum",
                        null=True,
                        default="1.0",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A minimum quantity for operationplans",
                    ),
                ),
                (
                    "sizemultiple",
                    models.DecimalField(
                        verbose_name="size multiple",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A multiple quantity for operationplans",
                    ),
                ),
                (
                    "sizemaximum",
                    models.DecimalField(
                        verbose_name="size maximum",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A maximum quantity for operationplans",
                    ),
                ),
                (
                    "cost",
                    models.DecimalField(
                        verbose_name="cost",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Cost per operationplan unit",
                    ),
                ),
                (
                    "duration",
                    freppledb.common.fields.DurationField(
                        verbose_name="duration",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A fixed duration for the operation",
                    ),
                ),
                (
                    "duration_per",
                    freppledb.common.fields.DurationField(
                        verbose_name="duration per unit",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="A variable duration for the operation",
                    ),
                ),
                (
                    "search",
                    models.CharField(
                        verbose_name="search mode",
                        null=True,
                        max_length=20,
                        choices=[
                            ("PRIORITY", "priority"),
                            ("MINCOST", "minimum cost"),
                            ("MINPENALTY", "minimum penalty"),
                            ("MINCOSTPENALTY", "minimum cost plus penalty"),
                        ],
                        blank=True,
                        help_text="Method to select preferred alternate",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        verbose_name="location",
                        null=True,
                        blank=True,
                        to="input.Location",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "operation",
                "ordering": ["name"],
                "verbose_name_plural": "operations",
                "verbose_name": "operation",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="OperationPlan",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.IntegerField(
                        primary_key=True,
                        verbose_name="identifier",
                        serialize=False,
                        help_text="Unique identifier of an operationplan",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        verbose_name="status",
                        help_text="Status of the order",
                        max_length=20,
                        null=True,
                        choices=[
                            ("proposed", "proposed"),
                            ("confirmed", "confirmed"),
                            ("closed", "closed"),
                        ],
                    ),
                ),
                (
                    "reference",
                    models.CharField(
                        null=True,
                        verbose_name="reference",
                        blank=True,
                        max_length=300,
                        help_text="External reference of this order",
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=15,
                        verbose_name="quantity",
                        default="1.00",
                        decimal_places=4,
                    ),
                ),
                (
                    "startdate",
                    models.DateTimeField(
                        null=True,
                        verbose_name="start date",
                        blank=True,
                        help_text="start date",
                    ),
                ),
                (
                    "enddate",
                    models.DateTimeField(
                        null=True,
                        verbose_name="end date",
                        blank=True,
                        help_text="end date",
                    ),
                ),
                (
                    "criticality",
                    models.DecimalField(
                        null=True,
                        max_digits=15,
                        verbose_name="criticality",
                        blank=True,
                        decimal_places=4,
                    ),
                ),
                (
                    "operation",
                    models.ForeignKey(
                        verbose_name="operation",
                        to="input.Operation",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        verbose_name="owner",
                        related_name="xchildren",
                        null=True,
                        blank=True,
                        to="input.OperationPlan",
                        help_text="Hierarchical parent",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "operationplan",
                "ordering": ["id"],
                "verbose_name_plural": "operationplans",
                "verbose_name": "operationplan",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="PurchaseOrder",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.IntegerField(
                        primary_key=True,
                        verbose_name="identifier",
                        serialize=False,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "reference",
                    models.CharField(
                        null=True,
                        verbose_name="reference",
                        blank=True,
                        max_length=300,
                        help_text="External reference of this order",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        verbose_name="status",
                        help_text="Status of the order",
                        max_length=20,
                        null=True,
                        choices=[
                            ("proposed", "proposed"),
                            ("confirmed", "confirmed"),
                            ("closed", "closed"),
                        ],
                    ),
                ),
                (
                    "quantity",
                    models.DecimalField(
                        max_digits=15,
                        verbose_name="quantity",
                        default="1.00",
                        decimal_places=4,
                    ),
                ),
                (
                    "startdate",
                    models.DateTimeField(
                        null=True,
                        verbose_name="start date",
                        blank=True,
                        help_text="start date",
                    ),
                ),
                (
                    "enddate",
                    models.DateTimeField(
                        null=True,
                        verbose_name="end date",
                        blank=True,
                        help_text="end date",
                    ),
                ),
                (
                    "criticality",
                    models.DecimalField(
                        null=True,
                        max_digits=15,
                        verbose_name="criticality",
                        blank=True,
                        decimal_places=4,
                    ),
                ),
                (
                    "item",
                    models.ForeignKey(
                        verbose_name="item", to="input.Item", on_delete=models.CASCADE
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        verbose_name="location",
                        to="input.Location",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "purchase_order",
                "ordering": ["id"],
                "verbose_name_plural": "purchase orders",
                "verbose_name": "purchase order",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Resource",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        verbose_name="type",
                        null=True,
                        default="default",
                        choices=[
                            ("default", "Default"),
                            ("buckets", "Buckets"),
                            ("infinite", "Infinite"),
                        ],
                        blank=True,
                        max_length=20,
                    ),
                ),
                (
                    "maximum",
                    models.DecimalField(
                        verbose_name="maximum",
                        null=True,
                        default="1.00",
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Size of the resource",
                    ),
                ),
                (
                    "cost",
                    models.DecimalField(
                        verbose_name="cost",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Cost for using 1 unit of the resource for 1 hour",
                    ),
                ),
                (
                    "maxearly",
                    freppledb.common.fields.DurationField(
                        verbose_name="max early",
                        null=True,
                        max_digits=15,
                        decimal_places=0,
                        blank=True,
                        help_text="Time window before the ask date where we look for available capacity",
                    ),
                ),
                (
                    "setup",
                    models.CharField(
                        null=True,
                        verbose_name="setup",
                        blank=True,
                        max_length=300,
                        help_text="Setup of the resource at the start of the plan",
                    ),
                ),
                (
                    "location",
                    models.ForeignKey(
                        verbose_name="location",
                        null=True,
                        blank=True,
                        to="input.Location",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "maximum_calendar",
                    models.ForeignKey(
                        verbose_name="maximum calendar",
                        null=True,
                        blank=True,
                        to="input.Calendar",
                        help_text="Calendar defining the resource size varying over time",
                        on_delete=models.SET_NULL,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        verbose_name="owner",
                        related_name="xchildren",
                        null=True,
                        blank=True,
                        to="input.Resource",
                        help_text="Hierarchical parent",
                        on_delete=models.SET_NULL,
                    ),
                ),
            ],
            options={
                "db_table": "resource",
                "ordering": ["name"],
                "verbose_name_plural": "resources",
                "verbose_name": "resource",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="ResourceSkill",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "effective_start",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective start",
                        blank=True,
                        help_text="Validity start date",
                    ),
                ),
                (
                    "effective_end",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective end",
                        blank=True,
                        help_text="Validity end date",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        null=True,
                        blank=True,
                        verbose_name="priority",
                        default=1,
                        help_text="Priority of this skill in a group of alternates",
                    ),
                ),
                (
                    "resource",
                    models.ForeignKey(
                        related_name="skills",
                        verbose_name="resource",
                        to="input.Resource",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "resourceskill",
                "verbose_name_plural": "resource skills",
                "abstract": False,
                "ordering": ["resource", "skill"],
                "verbose_name": "resource skill",
            },
        ),
        migrations.CreateModel(
            name="SetupMatrix",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                    ),
                ),
            ],
            options={
                "db_table": "setupmatrix",
                "ordering": ["name"],
                "verbose_name_plural": "setup matrices",
                "verbose_name": "setup matrix",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SetupRule",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        verbose_name="ID",
                        serialize=False,
                        primary_key=True,
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                ("priority", models.IntegerField(verbose_name="priority")),
                (
                    "fromsetup",
                    models.CharField(
                        null=True,
                        verbose_name="from setup",
                        blank=True,
                        max_length=300,
                        help_text="Name of the old setup (wildcard characters are supported)",
                    ),
                ),
                (
                    "tosetup",
                    models.CharField(
                        null=True,
                        verbose_name="to setup",
                        blank=True,
                        max_length=300,
                        help_text="Name of the new setup (wildcard characters are supported)",
                    ),
                ),
                (
                    "duration",
                    freppledb.common.fields.DurationField(
                        verbose_name="duration",
                        null=True,
                        max_digits=15,
                        decimal_places=0,
                        blank=True,
                        help_text="Duration of the changeover",
                    ),
                ),
                (
                    "cost",
                    models.DecimalField(
                        verbose_name="cost",
                        null=True,
                        max_digits=15,
                        decimal_places=4,
                        blank=True,
                        help_text="Cost of the conversion",
                    ),
                ),
                (
                    "setupmatrix",
                    models.ForeignKey(
                        related_name="rules",
                        verbose_name="setup matrix",
                        to="input.SetupMatrix",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "setuprule",
                "verbose_name_plural": "setup matrix rules",
                "abstract": False,
                "ordering": ["priority"],
                "verbose_name": "setup matrix rule",
            },
        ),
        migrations.CreateModel(
            name="Skill",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
            ],
            options={
                "db_table": "skill",
                "ordering": ["name"],
                "verbose_name_plural": "skills",
                "verbose_name": "skill",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SubOperation",
            fields=[
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "id",
                    models.AutoField(
                        primary_key=True, verbose_name="identifier", serialize=False
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        verbose_name="priority",
                        default=1,
                        help_text="Sequence of this operation among the suboperations. Negative values are ignored.",
                    ),
                ),
                (
                    "effective_start",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective start",
                        blank=True,
                        help_text="Validity start date",
                    ),
                ),
                (
                    "effective_end",
                    models.DateTimeField(
                        null=True,
                        verbose_name="effective end",
                        blank=True,
                        help_text="Validity end date",
                    ),
                ),
                (
                    "operation",
                    models.ForeignKey(
                        related_name="suboperations",
                        verbose_name="operation",
                        to="input.Operation",
                        help_text="Parent operation",
                        on_delete=models.CASCADE,
                    ),
                ),
                (
                    "suboperation",
                    models.ForeignKey(
                        related_name="superoperations",
                        verbose_name="suboperation",
                        to="input.Operation",
                        help_text="Child operation",
                        on_delete=models.CASCADE,
                    ),
                ),
            ],
            options={
                "db_table": "suboperation",
                "ordering": ["operation", "priority", "suboperation"],
                "verbose_name_plural": "suboperations",
                "verbose_name": "suboperation",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Supplier",
            fields=[
                (
                    "lft",
                    models.PositiveIntegerField(
                        editable=False, blank=True, null=True, db_index=True
                    ),
                ),
                (
                    "rght",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "lvl",
                    models.PositiveIntegerField(editable=False, null=True, blank=True),
                ),
                (
                    "name",
                    models.CharField(
                        primary_key=True,
                        verbose_name="name",
                        serialize=False,
                        max_length=300,
                        help_text="Unique identifier",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="source",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "lastmodified",
                    models.DateTimeField(
                        editable=False,
                        db_index=True,
                        verbose_name="last modified",
                        default=django.utils.timezone.now,
                    ),
                ),
                (
                    "description",
                    models.CharField(
                        null=True,
                        verbose_name="description",
                        blank=True,
                        max_length=500,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="category",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "subcategory",
                    models.CharField(
                        null=True,
                        blank=True,
                        verbose_name="subcategory",
                        db_index=True,
                        max_length=300,
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        verbose_name="owner",
                        related_name="xchildren",
                        null=True,
                        blank=True,
                        to="input.Supplier",
                        help_text="Hierarchical parent",
                        on_delete=models.SET_NULL,
                    ),
                ),
            ],
            options={
                "db_table": "supplier",
                "ordering": ["name"],
                "verbose_name_plural": "suppliers",
                "verbose_name": "supplier",
                "abstract": False,
            },
        ),
        migrations.AddField(
            model_name="resourceskill",
            name="skill",
            field=models.ForeignKey(
                related_name="resources",
                verbose_name="skill",
                to="input.Skill",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="resource",
            name="setupmatrix",
            field=models.ForeignKey(
                verbose_name="setup matrix",
                null=True,
                blank=True,
                to="input.SetupMatrix",
                help_text="Setup matrix defining the conversion time and cost",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="purchaseorder",
            name="supplier",
            field=models.ForeignKey(
                verbose_name="supplier", to="input.Supplier", on_delete=models.CASCADE
            ),
        ),
        migrations.AddField(
            model_name="load",
            name="operation",
            field=models.ForeignKey(
                related_name="loads",
                verbose_name="operation",
                to="input.Operation",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="load",
            name="resource",
            field=models.ForeignKey(
                related_name="loads",
                verbose_name="resource",
                to="input.Resource",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="load",
            name="skill",
            field=models.ForeignKey(
                verbose_name="skill",
                related_name="loads",
                null=True,
                blank=True,
                to="input.Skill",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="itemsupplier",
            name="location",
            field=models.ForeignKey(
                verbose_name="location",
                related_name="itemsuppliers",
                null=True,
                blank=True,
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="itemsupplier",
            name="supplier",
            field=models.ForeignKey(
                related_name="suppliers",
                verbose_name="supplier",
                to="input.Supplier",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="itemdistribution",
            name="location",
            field=models.ForeignKey(
                verbose_name="location",
                related_name="itemdistributions_destination",
                null=True,
                blank=True,
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="itemdistribution",
            name="origin",
            field=models.ForeignKey(
                related_name="itemdistributions_origin",
                verbose_name="origin",
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="operation",
            field=models.ForeignKey(
                verbose_name="delivery operation",
                null=True,
                blank=True,
                to="input.Operation",
                help_text="Default operation used to ship a demand for this item",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="item",
            name="owner",
            field=models.ForeignKey(
                verbose_name="owner",
                related_name="xchildren",
                null=True,
                blank=True,
                to="input.Item",
                help_text="Hierarchical parent",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="flow",
            name="operation",
            field=models.ForeignKey(
                related_name="flows",
                verbose_name="operation",
                to="input.Operation",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="flow",
            name="thebuffer",
            field=models.ForeignKey(
                related_name="flows",
                verbose_name="buffer",
                to="input.Buffer",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="distributionorder",
            name="destination",
            field=models.ForeignKey(
                related_name="destinations",
                verbose_name="destination",
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="distributionorder",
            name="item",
            field=models.ForeignKey(
                verbose_name="item", to="input.Item", on_delete=models.CASCADE
            ),
        ),
        migrations.AddField(
            model_name="distributionorder",
            name="origin",
            field=models.ForeignKey(
                verbose_name="origin",
                related_name="origins",
                null=True,
                blank=True,
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="demand",
            name="item",
            field=models.ForeignKey(
                verbose_name="item",
                null=True,
                blank=True,
                to="input.Item",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="demand",
            name="location",
            field=models.ForeignKey(
                verbose_name="location",
                null=True,
                blank=True,
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="demand",
            name="operation",
            field=models.ForeignKey(
                verbose_name="delivery operation",
                related_name="used_demand",
                null=True,
                blank=True,
                to="input.Operation",
                help_text="Operation used to satisfy this demand",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="demand",
            name="owner",
            field=models.ForeignKey(
                verbose_name="owner",
                related_name="xchildren",
                null=True,
                blank=True,
                to="input.Demand",
                help_text="Hierarchical parent",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="buffer",
            name="item",
            field=models.ForeignKey(
                verbose_name="item",
                null=True,
                to="input.Item",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="buffer",
            name="location",
            field=models.ForeignKey(
                verbose_name="location",
                null=True,
                blank=True,
                to="input.Location",
                on_delete=models.CASCADE,
            ),
        ),
        migrations.AddField(
            model_name="buffer",
            name="minimum_calendar",
            field=models.ForeignKey(
                verbose_name="minimum calendar",
                null=True,
                blank=True,
                to="input.Calendar",
                help_text="Calendar storing a time-dependent safety stock profile",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="buffer",
            name="owner",
            field=models.ForeignKey(
                verbose_name="owner",
                related_name="xchildren",
                null=True,
                blank=True,
                to="input.Buffer",
                help_text="Hierarchical parent",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AddField(
            model_name="buffer",
            name="producing",
            field=models.ForeignKey(
                verbose_name="producing",
                related_name="used_producing",
                null=True,
                blank=True,
                to="input.Operation",
                help_text="Operation to replenish the buffer",
                on_delete=models.SET_NULL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="setuprule", unique_together=set([("setupmatrix", "priority")])
        ),
        migrations.AlterUniqueTogether(
            name="resourceskill", unique_together=set([("resource", "skill")])
        ),
        migrations.AlterUniqueTogether(
            name="load", unique_together=set([("operation", "resource")])
        ),
        migrations.AlterUniqueTogether(
            name="itemsupplier",
            unique_together=set([("item", "location", "supplier", "effective_start")]),
        ),
        migrations.AlterUniqueTogether(
            name="itemdistribution",
            unique_together=set([("item", "location", "origin", "effective_start")]),
        ),
        migrations.AlterUniqueTogether(
            name="flow", unique_together=set([("operation", "thebuffer")])
        ),
        migrations.RunPython(loadParameters),
    ]
