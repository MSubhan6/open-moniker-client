"""Smart pandas object creation based on data structure detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _pandas_available() -> bool:
    """Check if pandas is installed."""
    try:
        import pandas
        return True
    except ImportError:
        return False


@dataclass
class DataShape:
    """Analyzed data structure information."""
    row_count: int
    column_count: int
    columns: list[str]
    has_temporal_column: bool = False
    temporal_column_name: str | None = None
    single_value_column: str | None = None

    @property
    def is_scalar(self) -> bool:
        """Single row, single column."""
        return self.row_count == 1 and self.column_count == 1

    @property
    def is_vector(self) -> bool:
        """Single column, multiple rows."""
        return self.column_count == 1 and self.row_count > 1

    @property
    def is_timeseries(self) -> bool:
        """Has temporal column and single value column."""
        return (
            self.has_temporal_column
            and self.single_value_column is not None
            and self.column_count == 2
        )

    @property
    def is_matrix(self) -> bool:
        """Multiple columns."""
        return self.column_count > 1


def analyze_shape(
    data: list[dict[str, Any]],
    schema: dict[str, Any] | None = None,
    semantic_tags: list[str] | None = None,
) -> DataShape:
    """
    Analyze data structure from data, schema, and semantic tags.

    Args:
        data: List of dictionaries representing rows
        schema: Optional schema information with column metadata
        semantic_tags: Optional semantic tags from catalog

    Returns:
        DataShape object with analyzed structure
    """
    if not data:
        return DataShape(
            row_count=0,
            column_count=0,
            columns=[],
        )

    # Basic shape
    row_count = len(data)
    columns = list(data[0].keys()) if data else []
    column_count = len(columns)

    # Detect temporal columns from schema
    temporal_column_name = None
    has_temporal_column = False

    if schema and "columns" in schema:
        for col in schema["columns"]:
            col_type = col.get("type", "").lower()
            if col_type in ("datetime", "timestamp", "date"):
                temporal_column_name = col["name"]
                has_temporal_column = True
                break

    # Detect single value column (non-temporal column in 2-column dataset)
    single_value_column = None
    if column_count == 2 and temporal_column_name:
        for col in columns:
            if col != temporal_column_name:
                single_value_column = col
                break
    elif column_count == 1:
        single_value_column = columns[0]

    return DataShape(
        row_count=row_count,
        column_count=column_count,
        columns=columns,
        has_temporal_column=has_temporal_column,
        temporal_column_name=temporal_column_name,
        single_value_column=single_value_column,
    )


def _extract_scalar(data: list[dict[str, Any]]) -> Any:
    """Extract single scalar value from data."""
    if not data or not data[0]:
        return None
    # Get the first (and only) value from the first (and only) row
    return list(data[0].values())[0]


def _to_series(
    data: list[dict[str, Any]],
    column_name: str,
    name: str | None = None,
):
    """
    Convert to pandas Series.

    Args:
        data: List of dictionaries
        column_name: Column to extract
        name: Series name (defaults to column_name)
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for smart conversion. Install with: pip install pandas")

    values = [row[column_name] for row in data]
    return pd.Series(values, name=name or column_name)


def _to_timeseries(
    data: list[dict[str, Any]],
    temporal_column: str,
    value_column: str,
    name: str | None = None,
):
    """
    Convert to pandas Series with DatetimeIndex.

    Args:
        data: List of dictionaries
        temporal_column: Name of temporal column for index
        value_column: Name of value column for series
        name: Series name (defaults to value_column)
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for smart conversion. Install with: pip install pandas")

    # Extract temporal and value columns
    dates = [row[temporal_column] for row in data]
    values = [row[value_column] for row in data]

    # Create series with datetime index
    index = pd.to_datetime(dates)
    return pd.Series(values, index=index, name=name or value_column)


def _to_dataframe(data: list[dict[str, Any]]):
    """Convert to pandas DataFrame."""
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for smart conversion. Install with: pip install pandas")

    return pd.DataFrame(data)


def to_pandas_smart(
    data: list[dict[str, Any]],
    schema: dict[str, Any] | None = None,
    semantic_tags: list[str] | None = None,
) -> Any:
    """
    Convert data to the most appropriate pandas object based on structure.

    Detection hierarchy:
    1. Semantic tags (highest priority)
    2. Schema analysis
    3. Shape heuristics (fallback)

    Args:
        data: List of dictionaries representing rows
        schema: Optional schema information
        semantic_tags: Optional semantic tags

    Returns:
        Appropriate pandas object:
        - Scalar value for single value datasets
        - pd.Series for single column datasets
        - pd.Series with DatetimeIndex for timeseries
        - pd.DataFrame for multi-column datasets
    """
    if not _pandas_available():
        return data

    # Empty data
    if not data:
        import pandas as pd
        return pd.DataFrame()

    # Analyze shape
    shape = analyze_shape(data, schema, semantic_tags)

    # Tier 1: Semantic tags (explicit intent)
    if semantic_tags:
        if "scalar" in semantic_tags:
            return _extract_scalar(data)

        if "vector" in semantic_tags:
            if shape.single_value_column:
                return _to_series(data, shape.single_value_column)
            # Fall through to shape-based detection

        if "timeseries" in semantic_tags:
            if shape.is_timeseries:
                return _to_timeseries(
                    data,
                    shape.temporal_column_name,
                    shape.single_value_column,
                )
            # Fall through if structure doesn't match

    # Tier 2: Schema-based detection
    if shape.is_timeseries:
        return _to_timeseries(
            data,
            shape.temporal_column_name,
            shape.single_value_column,
        )

    # Tier 3: Shape heuristics
    if shape.is_scalar:
        return _extract_scalar(data)

    if shape.is_vector:
        return _to_series(data, shape.single_value_column)

    # Default: DataFrame for everything else
    return _to_dataframe(data)
