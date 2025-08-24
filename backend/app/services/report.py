
"""Report generation service."""

import io
from datetime import datetime, date
from typing import List, Dict, Any
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, Response

from app.models.unit_event import UnitEvent
from app.models.unit import Unit
from app.models.user import User
from app.models.location import Location


class ReportService:
    """Service for generating reports."""
    
    @staticmethod
    async def generate_movements_report(
        db: AsyncSession,
        from_date: date,
        to_date: date,
        format_type: str = "xlsx"
    ) -> Response:
        """Generate movements report for date range."""
        
        # Convert dates to datetime
        from_datetime = datetime.combine(from_date, datetime.min.time())
        to_datetime = datetime.combine(to_date, datetime.max.time())
        
        # Get unit events in date range
        query = select(UnitEvent).options(
            selectinload(UnitEvent.unit).selectinload(Unit.location),
            selectinload(UnitEvent.unit).selectinload(Unit.assigned_branch),
            selectinload(UnitEvent.unit).selectinload(Unit.shipment),
            selectinload(UnitEvent.user)
        ).where(
            and_(
                UnitEvent.timestamp >= from_datetime,
                UnitEvent.timestamp <= to_datetime
            )
        ).order_by(UnitEvent.timestamp.desc())
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        # Prepare report data
        report_data = []
        for event in events:
            # Extract location changes from before/after states
            from_location = ""
            to_location = ""
            
            if event.before and event.after:
                before_loc_id = event.before.get('location_id')
                after_loc_id = event.after.get('location_id')
                
                if before_loc_id != after_loc_id:
                    from_location = await ReportService._get_location_name(db, before_loc_id)
                    to_location = await ReportService._get_location_name(db, after_loc_id)
            
            report_data.append({
                'Fecha/Hora': event.timestamp.strftime('%d/%m/%Y %H:%M'),
                'ID Unidad': str(event.unit_id),
                'Tipo Evento': event.event_type.value,
                'De': from_location,
                'Hacia': to_location,
                'Usuario': event.user.name if event.user else '',
                'Lote': event.unit.shipment.batch_code if event.unit and event.unit.shipment else '',
                'Marca': event.unit.brand if event.unit else '',
                'Modelo': event.unit.model if event.unit else '',
                'Color': event.unit.color if event.unit else '',
                'No. Motor': event.unit.engine_number if event.unit else '',
                'No. Chasis': event.unit.chassis_number if event.unit else '',
                'Sucursal': event.unit.assigned_branch.name if event.unit and event.unit.assigned_branch else '',
                'Motivo': event.reason or '',
            })
        
        # Create DataFrame
        df = pd.DataFrame(report_data)
        
        # Generate file
        if format_type.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            content = output.getvalue()
            
            return Response(
                content=content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=movimientos_{from_date}_{to_date}.csv"
                }
            )
        
        else:  # xlsx
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Movimientos')
                
                # Auto-adjust column widths
                worksheet = writer.sheets['Movimientos']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            content = output.getvalue()
            
            return Response(
                content=content,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={
                    "Content-Disposition": f"attachment; filename=movimientos_{from_date}_{to_date}.xlsx"
                }
            )
    
    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> Dict[str, Any]:
        """Get dashboard statistics."""
        
        # Units by status
        status_query = select(Unit.status, Unit.id).distinct()
        status_result = await db.execute(status_query)
        status_data = {}
        
        for status, unit_id in status_result.fetchall():
            if status.value not in status_data:
                status_data[status.value] = 0
            status_data[status.value] += 1
        
        # Units by location
        location_query = select(Location.name, Unit.id).join(
            Unit, Unit.location_id == Location.id
        )
        location_result = await db.execute(location_query)
        location_data = {}
        
        for location_name, unit_id in location_result.fetchall():
            if location_name not in location_data:
                location_data[location_name] = 0
            location_data[location_name] += 1
        
        # Recent events (last 10)
        recent_events_query = select(UnitEvent).options(
            selectinload(UnitEvent.unit),
            selectinload(UnitEvent.user)
        ).order_by(UnitEvent.timestamp.desc()).limit(10)
        
        recent_events_result = await db.execute(recent_events_query)
        recent_events = []
        
        for event in recent_events_result.scalars().all():
            recent_events.append({
                'timestamp': event.timestamp.strftime('%d/%m/%Y %H:%M'),
                'event_type': event.event_type.value,
                'unit_id': str(event.unit_id),
                'user': event.user.name if event.user else '',
                'unit_info': f"{event.unit.brand} {event.unit.model}" if event.unit else ''
            })
        
        return {
            'units_by_status': status_data,
            'units_by_location': location_data,
            'recent_events': recent_events,
            'total_units': sum(status_data.values()),
        }
    
    @staticmethod
    async def _get_location_name(db: AsyncSession, location_id: int) -> str:
        """Get location name by ID."""
        if not location_id:
            return ""
        
        result = await db.execute(
            select(Location.name).where(Location.id == location_id)
        )
        location = result.scalar_one_or_none()
        return location or ""
