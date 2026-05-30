"""Query engine for video storage."""

import re
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass

from .exceptions import QueryError


@dataclass
class QueryResult:
    """Query result container."""

    columns: List[str]
    rows: List[List[Any]]
    row_count: int

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries."""
        result = []
        for row in self.rows:
            row_dict = dict(zip(self.columns, row))
            result.append(row_dict)
        return result

    def first(self) -> Optional[Dict[str, Any]]:
        """Get first row as dictionary."""
        if self.rows:
            return dict(zip(self.columns, self.rows[0]))
        return None


class VideoQuery:
    """Query engine for Video Database."""

    def __init__(self, video_db):
        self.video_db = video_db

    def select(
        self,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> QueryResult:
        """Execute SELECT query."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        # Stable 1-based rowid for SELECT / WHERE in the UI.
        raw_rows = self.video_db.crud.select_all()
        all_rows = [{**dict(row), "rowid": i + 1} for i, row in enumerate(raw_rows)]

        # Filter columns
        if columns is None:
            columns = self.video_db.get_column_names()

        # Apply WHERE clause
        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        # Apply ORDER BY
        if order_by:
            all_rows = self._apply_order_by(all_rows, order_by)

        # Apply LIMIT and OFFSET
        if offset > 0:
            all_rows = all_rows[offset:]
        if limit is not None:
            all_rows = all_rows[:limit]

        # Convert to result format
        result_rows = []
        for row in all_rows:
            row_values = []
            for col in columns:
                row_values.append(row.get(col, None))
            result_rows.append(row_values)

        return QueryResult(
            columns=columns, rows=result_rows, row_count=len(result_rows)
        )

    def count(self, where: Optional[str] = None) -> int:
        """Count rows with optional WHERE clause."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        raw_rows = self.video_db.crud.select_all()
        all_rows = [{**dict(row), "rowid": i + 1} for i, row in enumerate(raw_rows)]

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        return len(all_rows)

    def sum(self, column: str, where: Optional[str] = None) -> Union[int, float]:
        """Calculate sum of a column."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        col_def = self.video_db.schema.get_column(column)
        if not col_def:
            raise QueryError(f"Column '{column}' not found")

        if col_def.data_type not in ["INTEGER", "REAL"]:
            raise QueryError(f"Cannot sum non-numeric column '{column}'")

        all_rows = self.video_db.crud.select_all()

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        total: Union[int, float] = 0
        for row in all_rows:
            value = row.get(column, 0)
            if value is not None and value != "":
                total += float(value)

        return total

    def avg(self, column: str, where: Optional[str] = None) -> Optional[float]:
        """Calculate average of a column."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        col_def = self.video_db.schema.get_column(column)
        if not col_def:
            raise QueryError(f"Column '{column}' not found")

        if col_def.data_type not in ["INTEGER", "REAL"]:
            raise QueryError(f"Cannot average non-numeric column '{column}'")

        all_rows = self.video_db.crud.select_all()

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        if not all_rows:
            return None

        total: Union[int, float] = 0
        count = 0
        for row in all_rows:
            value = row.get(column, 0)
            if value is not None and value != "":
                total += float(value)
                count += 1

        return total / count if count > 0 else None

    def min(self, column: str, where: Optional[str] = None) -> Optional[Any]:
        """Find minimum value of a column."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        col_def = self.video_db.schema.get_column(column)
        if not col_def:
            raise QueryError(f"Column '{column}' not found")

        all_rows = self.video_db.crud.select_all()

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        if not all_rows:
            return None

        values = []
        for row in all_rows:
            value = row.get(column)
            if value is not None and value != "":
                values.append(value)

        if not values:
            return None

        # For numeric types, convert to numbers
        if col_def.data_type in ["INTEGER", "REAL"]:
            numeric_values = [float(v) for v in values]
            return min(numeric_values)
        else:
            return min(values)

    def max(self, column: str, where: Optional[str] = None) -> Optional[Any]:
        """Find maximum value of a column."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        col_def = self.video_db.schema.get_column(column)
        if not col_def:
            raise QueryError(f"Column '{column}' not found")

        all_rows = self.video_db.crud.select_all()

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        if not all_rows:
            return None

        values = []
        for row in all_rows:
            value = row.get(column)
            if value is not None and value != "":
                values.append(value)

        if not values:
            return None

        # For numeric types, convert to numbers
        if col_def.data_type in ["INTEGER", "REAL"]:
            numeric_values = [float(v) for v in values]
            return max(numeric_values)
        else:
            return max(values)

    def distinct(self, column: str, where: Optional[str] = None) -> List[Any]:
        """Get distinct values of a column."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        col_def = self.video_db.schema.get_column(column)
        if not col_def:
            raise QueryError(f"Column '{column}' not found")

        all_rows = self.video_db.crud.select_all()

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        values = set()
        for row in all_rows:
            value = row.get(column)
            if value is not None and value != "":
                values.add(value)

        return sorted(list(values))

    def group_by(
        self,
        columns: List[str],
        aggregates: Optional[Dict[str, str]] = None,
        where: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Group rows by columns with optional aggregations."""
        if not self.video_db.schema:
            raise QueryError("No schema defined")

        all_rows = self.video_db.crud.select_all()

        if where:
            all_rows = self._apply_where_clause(all_rows, where)

        # Group rows
        groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = {}
        for row in all_rows:
            # Create group key
            group_key = tuple(row.get(col) for col in columns)

            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(row)

        # Process aggregations
        result = []
        for group_key, group_rows in groups.items():
            group_result = {}

            # Add grouping columns
            for i, col in enumerate(columns):
                group_result[col] = group_key[i]

            # Add aggregations
            if aggregates:
                for agg_col, agg_func in aggregates.items():
                    col_def = self.video_db.schema.get_column(agg_col)
                    if not col_def:
                        continue

                    values = [row.get(agg_col) for row in group_rows]
                    numeric_values = [
                        float(v) for v in values if v is not None and v != ""
                    ]

                    if agg_func.lower() == "count":
                        group_result[f"{agg_func}_{agg_col}"] = len(
                            [v for v in values if v is not None and v != ""]
                        )
                    elif agg_func.lower() == "sum" and numeric_values:
                        group_result[f"{agg_func}_{agg_col}"] = sum(numeric_values)
                    elif agg_func.lower() == "avg" and numeric_values:
                        group_result[f"{agg_func}_{agg_col}"] = sum(
                            numeric_values
                        ) / len(numeric_values)
                    elif agg_func.lower() == "min" and numeric_values:
                        group_result[f"{agg_func}_{agg_col}"] = min(numeric_values)
                    elif agg_func.lower() == "max" and numeric_values:
                        group_result[f"{agg_func}_{agg_col}"] = max(numeric_values)

            result.append(group_result)

        return result

    def _apply_where_clause(
        self, rows: List[Dict[str, Any]], where_clause: str
    ) -> List[Dict[str, Any]]:
        """Apply WHERE clause to filter rows."""
        try:
            # Simple WHERE clause parser
            # Supports: column = value, column > value, column < value, column LIKE value
            # AND and OR operators (basic implementation)

            conditions = self._parse_where_clause(where_clause)
            filtered_rows = []

            for row in rows:
                if self._evaluate_conditions(row, conditions):
                    filtered_rows.append(row)

            return filtered_rows

        except Exception as e:
            raise QueryError(f"Invalid WHERE clause: {e}")

    def _parse_where_clause(self, where_clause: str) -> List[Dict[str, Any]]:
        """Parse WHERE clause into conditions."""
        # Remove extra whitespace
        where_clause = re.sub(r"\s+", " ", where_clause.strip())

        # Split by AND/OR (simplified)
        and_parts = re.split(r"\s+AND\s+", where_clause, flags=re.IGNORECASE)

        conditions = []
        for part in and_parts:
            or_parts = re.split(r"\s+OR\s+", part, flags=re.IGNORECASE)

            or_conditions = []
            for or_part in or_parts:
                # Parse individual condition
                condition = self._parse_single_condition(or_part)
                or_conditions.append(condition)

            if len(or_conditions) == 1:
                conditions.append(or_conditions[0])
            else:
                conditions.append({"type": "or", "conditions": or_conditions})

        return conditions

    def _parse_single_condition(self, condition: str) -> Dict[str, Any]:
        """Parse a single condition."""
        # Match patterns: column operator value
        pattern = r"^(\w+)\s*(=|>|<|>=|<=|!=|LIKE)\s*(.+)$"
        match = re.match(pattern, condition.strip(), re.IGNORECASE)

        if not match:
            raise QueryError(f"Invalid condition: {condition}")

        column = match.group(1)
        operator = match.group(2).upper()
        value = match.group(3).strip("'\"")

        return {
            "type": "condition",
            "column": column,
            "operator": operator,
            "value": value,
        }

    def _evaluate_conditions(
        self, row: Dict[str, Any], conditions: List[Dict[str, Any]]
    ) -> bool:
        """Evaluate conditions against a row."""
        if not conditions:
            return True

        # All conditions are ANDed together
        for condition in conditions:
            if condition["type"] == "condition":
                if not self._evaluate_single_condition(row, condition):
                    return False
            elif condition["type"] == "or":
                # OR conditions - at least one must be true
                or_result = False
                for or_condition in condition["conditions"]:
                    if self._evaluate_single_condition(row, or_condition):
                        or_result = True
                        break
                if not or_result:
                    return False

        return True

    def _evaluate_single_condition(
        self, row: Dict[str, Any], condition: Dict[str, Any]
    ) -> bool:
        """Evaluate a single condition."""
        column = condition["column"]
        operator = condition["operator"]
        value = condition["value"]

        # Get column value
        row_value = row.get(column)

        if column.lower() == "rowid":
            try:
                rv = int(row_value) if row_value is not None else 0
                cmp_val = int(float(value))
            except (TypeError, ValueError):
                return False
            if operator == "=":
                return rv == cmp_val
            if operator == "!=":
                return rv != cmp_val
            if operator == ">":
                return rv > cmp_val
            if operator == "<":
                return rv < cmp_val
            if operator == ">=":
                return rv >= cmp_val
            if operator == "<=":
                return rv <= cmp_val
            raise QueryError(f"Unsupported operator for rowid: {operator}")

        # Handle null values
        if row_value is None or row_value == "":
            if operator == "=" and value == "":
                return True
            elif operator == "!=" and value != "":
                return True
            else:
                return False

        # Convert to appropriate type
        col_def = self.video_db.schema.get_column(column)
        numeric_compare = False
        if col_def and col_def.data_type in ["INTEGER", "REAL"]:
            try:
                row_value = float(str(row_value).strip())
                value = float(str(value).strip())
                numeric_compare = True
            except (TypeError, ValueError):
                pass  # Fall back to string comparisons below

        # Evaluate condition
        if operator == "=":
            return str(row_value) == str(value)
        elif operator == "!=":
            return str(row_value) != str(value)
        elif operator == ">":
            if numeric_compare:
                return row_value > value
            return str(row_value) > str(value)
        elif operator == "<":
            if numeric_compare:
                return row_value < value
            return str(row_value) < str(value)
        elif operator == ">=":
            if numeric_compare:
                return row_value >= value
            return str(row_value) >= str(value)
        elif operator == "<=":
            if numeric_compare:
                return row_value <= value
            return str(row_value) <= str(value)
        elif operator == "LIKE":
            # Simple LIKE support (wildcards)
            pattern = value.replace("%", ".*").replace("_", ".")
            return bool(re.match(pattern, str(row_value), re.IGNORECASE))
        else:
            raise QueryError(f"Unsupported operator: {operator}")

    def _apply_order_by(
        self, rows: List[Dict[str, Any]], order_by: str
    ) -> List[Dict[str, Any]]:
        """Apply ORDER BY clause."""
        # Parse ORDER BY: column ASC/DESC
        parts = order_by.strip().split()
        if len(parts) not in [1, 2]:
            raise QueryError(f"Invalid ORDER BY clause: {order_by}")

        column = parts[0]
        direction = parts[1].upper() if len(parts) == 2 else "ASC"

        if direction not in ["ASC", "DESC"]:
            raise QueryError(f"Invalid sort direction: {direction}")

        # Get column definition for type
        col_def = self.video_db.schema.get_column(column)
        if not col_def:
            raise QueryError(f"Column '{column}' not found")

        # Sort rows
        reverse = direction == "DESC"

        if col_def.data_type in ["INTEGER", "REAL"]:
            # Numeric sort; non-numeric values sort after numbers (schema/data mismatch).
            def sort_key(row):
                value = row.get(column, 0)
                if value is None or value == "":
                    return (0, 0.0)
                try:
                    return (0, float(str(value).strip()))
                except (TypeError, ValueError):
                    return (1, str(value))

        else:
            # String sort
            def sort_key(row):
                return str(row.get(column, ""))

        return sorted(rows, key=sort_key, reverse=reverse)
