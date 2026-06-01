
"""Report generation service."""

import io
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc, or_, and_, cast, String
from fastapi import Response

from app.models.models import Unit, Location, Transfer, Import, UnitStatus, TransferStatus


class ReportService:
    """Service for generating reports."""

    @staticmethod
    def get_dashboard_stats(db: Session) -> dict:
        total_units = db.query(Unit).count()
        in_stock_units = db.query(Unit).filter(Unit.status == UnitStatus.AVAILABLE).count()
        sold_units = db.query(Unit).filter(Unit.status == UnitStatus.SOLD).count()
        in_transit_units = db.query(Unit).filter(Unit.status == UnitStatus.IN_TRANSIT).count()
        total_locations = db.query(Location).count()

        recent_transfers = db.query(Transfer).options(
            selectinload(Transfer.dispatched_by),
            selectinload(Transfer.received_by),
            selectinload(Transfer.origin_location),
            selectinload(Transfer.destination_location),
        ).order_by(desc(Transfer.dispatched_at)).limit(10).all()

        inventory_by_location = db.query(
            Location.name.label("location"),
            func.count(Unit.id).label("count"),
        ).join(Unit, Unit.current_location_id == Location.id, isouter=True) \
         .group_by(Location.id, Location.name).all()

        inventory_by_brand = db.query(
            Unit.brand.label("brand"),
            func.count(Unit.id).label("count"),
        ).group_by(Unit.brand).all()

        six_months_ago = datetime.now() - timedelta(days=180)
        sales_by_month = db.query(
            func.substr(cast(Unit.sold_date, String), 1, 7).label("month"),
            func.count(Unit.id).label("count"),
        ).filter(
            and_(Unit.status == UnitStatus.SOLD, Unit.sold_date >= six_months_ago)
        ).group_by(func.substr(cast(Unit.sold_date, String), 1, 7)) \
         .order_by(func.substr(cast(Unit.sold_date, String), 1, 7)).all()

        recent_imports = db.query(Import).options(
            selectinload(Import.user)
        ).order_by(desc(Import.import_date)).limit(5).all()

        active_transfers = db.query(Transfer).filter(
            Transfer.status.in_([TransferStatus.PENDING, TransferStatus.IN_TRANSIT])
        ).count()

        return {
            "units": {
                "total": total_units,
                "available": in_stock_units,
                "sold": sold_units,
                "in_transit": in_transit_units,
            },
            "locations": {"total": total_locations},
            "transfers": {"active": active_transfers},
            "recent_transfers": [
                {
                    "id": t.id,
                    "unit_engine": t.unit.engine_number if t.unit else None,
                    "origin_location": t.origin_location.name if t.origin_location else None,
                    "destination_location": t.destination_location.name if t.destination_location else None,
                    "dispatched_by": f"{t.dispatched_by.first_name} {t.dispatched_by.last_name}" if t.dispatched_by else None,
                    "received_by": f"{t.received_by.first_name} {t.received_by.last_name}" if t.received_by else None,
                    "status": t.status,
                    "dispatched_at": t.dispatched_at,
                    "received_at": t.received_at,
                }
                for t in recent_transfers
            ],
            "inventory_by_location": [
                {"location": item.location, "count": item.count}
                for item in inventory_by_location
            ],
            "inventory_by_brand": [
                {"brand": item.brand, "count": item.count}
                for item in inventory_by_brand
            ],
            "sales_by_month": [
                {
                    "month": item.month if item.month else None,
                    "count": item.count,
                }
                for item in sales_by_month
            ],
            "recent_imports": [
                {
                    "id": imp.id,
                    "filename": imp.original_filename,
                    "total_records": imp.total_records,
                    "successful": imp.successful_imports,
                    "failed": imp.failed_imports,
                    "date": imp.import_date,
                    "user": f"{imp.user.first_name} {imp.user.last_name}" if imp.user else None,
                }
                for imp in recent_imports
            ],
        }

    @staticmethod
    def get_inventory_report(
        db: Session,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        color: Optional[str] = None,
        location_id: Optional[int] = None,
        status: Optional[UnitStatus] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        query = db.query(Unit).options(selectinload(Unit.current_location))

        if brand:
            query = query.filter(Unit.brand == brand)
        if model:
            query = query.filter(Unit.model == model)
        if color:
            query = query.filter(Unit.color == color)
        if location_id:
            query = query.filter(Unit.current_location_id == location_id)
        if status:
            query = query.filter(Unit.status == status)
        if date_from:
            query = query.filter(Unit.created_at >= date_from)
        if date_to:
            query = query.filter(Unit.created_at <= date_to)

        units = query.all()

        by_status = {}
        by_location = {}
        for unit in units:
            status_key = unit.status.value if unit.status else "unknown"
            by_status[status_key] = by_status.get(status_key, 0) + 1
            location_key = unit.current_location.name if unit.current_location else "No Location"
            by_location[location_key] = by_location.get(location_key, 0) + 1

        return {
            "total_units": len(units),
            "summary": {
                "by_status": by_status,
                "by_location": by_location,
            },
            "units": [
                {
                    "id": unit.id,
                    "engine_number": unit.engine_number,
                    "chassis_number": unit.chassis_number,
                    "brand": unit.brand,
                    "model": unit.model,
                    "color": unit.color,
                    "location": unit.current_location.name if unit.current_location else None,
                    "status": unit.status.value if unit.status else None,
                    "created_at": unit.created_at,
                    "sold_date": unit.sold_date,
                }
                for unit in units
            ],
        }

    @staticmethod
    def get_transfers_report(
        db: Session,
        user_id: Optional[int] = None,
        location_id: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        query = db.query(Transfer).options(
            selectinload(Transfer.dispatched_by),
            selectinload(Transfer.received_by),
            selectinload(Transfer.origin_location),
            selectinload(Transfer.destination_location),
        )

        if user_id:
            query = query.filter(
                or_(Transfer.dispatched_by_id == user_id, Transfer.received_by_id == user_id)
            )
        if location_id:
            query = query.filter(
                or_(
                    Transfer.origin_location_id == location_id,
                    Transfer.destination_location_id == location_id,
                )
            )
        if date_from:
            query = query.filter(Transfer.dispatched_at >= date_from)
        if date_to:
            query = query.filter(Transfer.dispatched_at <= date_to)

        total_transfers = query.count()
        transfers = query.order_by(desc(Transfer.dispatched_at)).offset(skip).limit(limit).all()

        by_status = db.query(
            Transfer.status, func.count(Transfer.id).label("count")
        ).group_by(Transfer.status).all()

        by_month = db.query(
            func.substr(cast(Transfer.dispatched_at, String), 1, 7).label("month"),
            func.count(Transfer.id).label("count"),
        ).group_by(func.substr(cast(Transfer.dispatched_at, String), 1, 7)) \
         .order_by(func.substr(cast(Transfer.dispatched_at, String), 1, 7)).all()

        return {
            "total_transfers": total_transfers,
            "summary": {
                "by_status": {item.status.value: item.count for item in by_status},
                "by_month": [
                    {"month": item.month if item.month else None, "count": item.count}
                    for item in by_month
                ],
            },
            "transfers": [
                {
                    "id": t.id,
                    "unit_id": t.unit_id,
                    "dispatched_by_id": t.dispatched_by_id,
                    "received_by_id": t.received_by_id,
                    "origin_location_id": t.origin_location_id,
                    "destination_location_id": t.destination_location_id,
                    "status": t.status.value if t.status else None,
                    "dispatched_at": t.dispatched_at,
                    "received_at": t.received_at,
                }
                for t in transfers
            ],
            "pagination": {
                "skip": skip,
                "limit": limit,
                "total": total_transfers,
                "has_next": skip + limit < total_transfers,
                "has_previous": skip > 0,
            },
        }

    @staticmethod
    def get_sales_report(
        db: Session,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        location_id: Optional[int] = None,
    ) -> dict:
        query = db.query(Unit).options(
            selectinload(Unit.current_location)
        ).filter(Unit.status == UnitStatus.SOLD)

        if date_from:
            query = query.filter(Unit.sold_date >= date_from)
        if date_to:
            query = query.filter(Unit.sold_date <= date_to)
        if location_id:
            sold_units_sub = db.query(Transfer.unit_id).filter(
                or_(
                    Transfer.origin_location_id == location_id,
                    Transfer.destination_location_id == location_id,
                )
            ).subquery()
            query = query.filter(Unit.id.in_(sold_units_sub))

        sold_units = query.all()

        sales_by_month = {}
        for unit in sold_units:
            if unit.sold_date:
                month_key = unit.sold_date.strftime("%Y-%m")
                sales_by_month.setdefault(month_key, {"count": 0})
                sales_by_month[month_key]["count"] += 1

        return {
            "total_sales": len(sold_units),
            "summary": {
                "by_month": [
                    {"month": month, "count": data["count"]}
                    for month, data in sorted(sales_by_month.items())
                ],
            },
            "sales": [
                {
                    "id": unit.id,
                    "engine_number": unit.engine_number,
                    "chassis_number": unit.chassis_number,
                    "brand": unit.brand,
                    "model": unit.model,
                    "color": unit.color,
                    "sold_date": unit.sold_date,
                }
                for unit in sold_units
            ],
        }

    @staticmethod
    def _prepare_df_for_excel(df: pd.DataFrame) -> pd.DataFrame:
        for col in df.columns:
            if df[col].dtype.name.startswith("datetime"):
                df[col] = df[col].apply(lambda x: x.replace(tzinfo=None) if pd.notna(x) and hasattr(x, 'tzinfo') and x.tzinfo is not None else x)
        return df

    @staticmethod
    def export_inventory_excel(
        db: Session,
        brand: Optional[str] = None,
        model: Optional[str] = None,
        location_id: Optional[int] = None,
        status: Optional[UnitStatus] = None,
    ) -> Response:
        report_data = ReportService.get_inventory_report(
            db, brand=brand, model=model, location_id=location_id, status=status
        )

        df = ReportService._prepare_df_for_excel(pd.DataFrame(report_data["units"]))
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Inventory', index=False)

            summary_data = []
            for category, data in report_data["summary"].items():
                for key, value in data.items():
                    summary_data.append({"Category": category, "Item": key, "Count": value})
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        output.seek(0)
        filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @staticmethod
    def export_transfers_excel(
        db: Session,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Response:
        report_data = ReportService.get_transfers_report(
            db, date_from=date_from, date_to=date_to, limit=10000
        )

        df = ReportService._prepare_df_for_excel(pd.DataFrame(report_data["transfers"]))
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Transfers', index=False)

        output.seek(0)
        filename = f"transfers_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @staticmethod
    def export_sales_excel(
        db: Session,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        location_id: Optional[int] = None,
    ) -> Response:
        report_data = ReportService.get_sales_report(
            db, date_from=date_from, date_to=date_to, location_id=location_id
        )

        df = ReportService._prepare_df_for_excel(pd.DataFrame(report_data["sales"]))
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Sales', index=False)

            summary_data = []
            for item in report_data["summary"]["by_month"]:
                summary_data.append({"Month": item["month"], "Count": item["count"]})
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

        output.seek(0)
        filename = f"sales_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return Response(
            content=output.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
