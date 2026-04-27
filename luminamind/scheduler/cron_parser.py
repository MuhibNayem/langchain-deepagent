from dataclasses import dataclass
from datetime import datetime


@dataclass
class CronExpression:
    minute: str  # 0-59, */5, etc.
    hour: str    # 0-23, */2, etc.
    day_of_month: str  # 1-31, */3, etc.
    month: str   # 1-12, */2, etc.
    day_of_week: str  # 0-6, mon-fri, etc.
    
    def validate(self) -> bool:
        """Validate cron fields."""
        try:
            self._parse_field(self.minute, 0, 59)
            self._parse_field(self.hour, 0, 23)
            self._parse_field(self.day_of_month, 1, 31)
            self._parse_field(self.month, 1, 12)
            self._parse_field(self.day_of_week, 0, 6)
            return True
        except ValueError:
            return False
    
    def _parse_field(self, field: str, min_val: int, max_val: int) -> set[int]:
        """Parse a single cron field into set of values."""
        values = set()
        
        for part in field.split(","):
            if part == "*":
                values.update(range(min_val, max_val + 1))
            elif part.startswith("*/"):
                step = int(part[2:])
                if step <= 0:
                    raise ValueError(f"Invalid step: {step}")
                values.update(range(min_val, max_val + 1, step))
            elif "-" in part:
                start, end = part.split("-")
                start_int, end_int = int(start), int(end)
                if start_int < min_val or end_int > max_val or start_int > end_int:
                    raise ValueError(f"Range {start}-{end} out of bounds ({min_val}-{max_val})")
                values.update(range(start_int, end_int + 1))
            else:
                val = int(part)
                if val < min_val or val > max_val:
                    raise ValueError(f"Value {val} out of bounds ({min_val}-{max_val})")
                values.add(val)
        
        return values
    
    def next_fire_time(self, from_time: datetime) -> datetime:
        """Calculate next firing time after from_time."""
        if not self.validate():
            raise ValueError("Invalid cron expression")
        
        minute_vals = self._parse_field(self.minute, 0, 59)
        hour_vals = self._parse_field(self.hour, 0, 23)
        day_vals = self._parse_field(self.day_of_month, 1, 31)
        month_vals = self._parse_field(self.month, 1, 12)
        dow_vals = self._parse_field(self.day_of_week, 0, 6)
        
        current = from_time.replace(second=0, microsecond=0)
        
        # Advance to next minute
        current = current.replace(minute=(current.minute + 1) % 60)
        if current.minute == 0:
            current = current.replace(hour=(current.hour + 1) % 24)
            if current.hour == 0:
                current = current.replace(day=current.day + 1)
        
        # Simple search (up to 1 year)
        for _ in range(60 * 24 * 366):
            if (current.month in month_vals and 
                current.day in day_vals and 
                current.hour in hour_vals and
                current.minute in minute_vals and
                current.weekday() in dow_vals):
                return current
            
            current = current.replace(minute=(current.minute + 1) % 60)
            if current.minute == 0:
                current = current.replace(hour=(current.hour + 1) % 24)
                if current.hour == 0:
                    current = current.replace(day=current.day + 1)
                    if current.day > 28:
                        # Simple: just increment, real impl handles month lengths
                        pass
        
        raise ValueError("No firing time found within 1 year")


def parse_cron(expression: str) -> CronExpression:
    """Parse a cron expression string into CronExpression object."""
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError("Cron expression must have 5 fields: minute hour day_of_month month day_of_week")
    
    return CronExpression(
        minute=parts[0],
        hour=parts[1],
        day_of_month=parts[2],
        month=parts[3],
        day_of_week=parts[4],
    )
