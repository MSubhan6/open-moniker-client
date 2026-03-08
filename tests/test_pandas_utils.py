"""Tests for smart pandas conversion utilities."""

from __future__ import annotations

import pytest

from moniker_client.pandas_utils import (
    analyze_shape,
    to_pandas_smart,
    _pandas_available,
)


# Skip all tests if pandas not available
pytestmark = pytest.mark.skipif(not _pandas_available(), reason="pandas not installed")


def test_analyze_shape_scalar():
    """Test scalar detection (1 row, 1 column)."""
    data = [{"pi": 3.14159}]
    shape = analyze_shape(data)

    assert shape.row_count == 1
    assert shape.column_count == 1
    assert shape.is_scalar is True
    assert shape.is_vector is False
    assert shape.is_matrix is False


def test_analyze_shape_vector():
    """Test vector detection (1 column, multiple rows)."""
    data = [
        {"price": 100},
        {"price": 101},
        {"price": 102},
    ]
    shape = analyze_shape(data)

    assert shape.row_count == 3
    assert shape.column_count == 1
    assert shape.is_scalar is False
    assert shape.is_vector is True
    assert shape.single_value_column == "price"


def test_analyze_shape_timeseries():
    """Test timeseries detection from schema."""
    data = [
        {"date": "2024-01-01", "close": 150.25},
        {"date": "2024-01-02", "close": 151.30},
    ]
    schema = {
        "columns": [
            {"name": "date", "type": "datetime"},
            {"name": "close", "type": "float"},
        ]
    }
    shape = analyze_shape(data, schema=schema)

    assert shape.row_count == 2
    assert shape.column_count == 2
    assert shape.has_temporal_column is True
    assert shape.temporal_column_name == "date"
    assert shape.single_value_column == "close"
    assert shape.is_timeseries is True


def test_analyze_shape_matrix():
    """Test matrix detection (multiple columns)."""
    data = [
        {"symbol": "AAPL", "price": 150, "volume": 1000},
        {"symbol": "GOOGL", "price": 2800, "volume": 500},
    ]
    shape = analyze_shape(data)

    assert shape.row_count == 2
    assert shape.column_count == 3
    assert shape.is_matrix is True


def test_analyze_shape_empty():
    """Test empty data handling."""
    data = []
    shape = analyze_shape(data)

    assert shape.row_count == 0
    assert shape.column_count == 0
    assert shape.columns == []


def test_to_pandas_smart_scalar():
    """Test scalar conversion - should return raw value."""
    import pandas as pd

    data = [{"pi": 3.14159}]
    result = to_pandas_smart(data, semantic_tags=["scalar"])

    assert result == 3.14159
    assert not isinstance(result, (pd.Series, pd.DataFrame))


def test_to_pandas_smart_scalar_heuristic():
    """Test scalar detection without semantic tag."""
    data = [{"value": 42}]
    result = to_pandas_smart(data)

    assert result == 42


def test_to_pandas_smart_vector():
    """Test vector conversion to Series."""
    import pandas as pd

    data = [
        {"price": 100},
        {"price": 101},
        {"price": 102},
    ]
    result = to_pandas_smart(data, semantic_tags=["vector"])

    assert isinstance(result, pd.Series)
    assert result.name == "price"
    assert len(result) == 3
    assert result.tolist() == [100, 101, 102]


def test_to_pandas_smart_vector_heuristic():
    """Test vector detection without semantic tag."""
    import pandas as pd

    data = [{"score": 10}, {"score": 20}, {"score": 30}]
    result = to_pandas_smart(data)

    assert isinstance(result, pd.Series)
    assert result.name == "score"


def test_to_pandas_smart_timeseries():
    """Test timeseries conversion with DatetimeIndex."""
    import pandas as pd

    data = [
        {"date": "2024-01-01", "close": 150.25},
        {"date": "2024-01-02", "close": 151.30},
        {"date": "2024-01-03", "close": 149.80},
    ]
    schema = {
        "columns": [
            {"name": "date", "type": "datetime"},
            {"name": "close", "type": "float"},
        ]
    }
    result = to_pandas_smart(data, schema=schema, semantic_tags=["timeseries"])

    assert isinstance(result, pd.Series)
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.name == "close"
    assert len(result) == 3
    assert result.iloc[0] == 150.25


def test_to_pandas_smart_timeseries_schema_only():
    """Test timeseries detection from schema without semantic tag."""
    import pandas as pd

    data = [
        {"timestamp": "2024-01-01", "value": 100},
        {"timestamp": "2024-01-02", "value": 200},
    ]
    schema = {
        "columns": [
            {"name": "timestamp", "type": "timestamp"},
            {"name": "value", "type": "integer"},
        ]
    }
    result = to_pandas_smart(data, schema=schema)

    assert isinstance(result, pd.Series)
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.name == "value"


def test_to_pandas_smart_dataframe():
    """Test DataFrame fallback for multi-column data."""
    import pandas as pd

    data = [
        {"symbol": "AAPL", "price": 150, "volume": 1000},
        {"symbol": "GOOGL", "price": 2800, "volume": 500},
    ]
    result = to_pandas_smart(data)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result.columns) == ["symbol", "price", "volume"]


def test_to_pandas_smart_empty():
    """Test empty data returns empty DataFrame."""
    import pandas as pd

    data = []
    result = to_pandas_smart(data)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 0


def test_to_pandas_smart_semantic_tag_override():
    """Test semantic tag overrides shape heuristics."""
    import pandas as pd

    # Data that looks like a matrix, but tagged as scalar
    data = [{"value": 42}]
    result = to_pandas_smart(data, semantic_tags=["scalar"])

    assert result == 42
    assert not isinstance(result, pd.DataFrame)


def test_to_pandas_smart_timeseries_fallback():
    """Test timeseries tag without proper structure falls back."""
    import pandas as pd

    # Tagged as timeseries but doesn't have temporal column
    data = [
        {"symbol": "AAPL", "price": 150, "volume": 1000},
    ]
    result = to_pandas_smart(data, semantic_tags=["timeseries"])

    # Should fall back to DataFrame
    assert isinstance(result, pd.DataFrame)


def test_to_pandas_smart_date_type_variants():
    """Test different datetime type names in schema."""
    import pandas as pd

    test_cases = [
        "datetime",
        "timestamp",
        "date",
        "DATETIME",  # Case insensitive
    ]

    for date_type in test_cases:
        data = [
            {"time": "2024-01-01", "value": 100},
            {"time": "2024-01-02", "value": 200},
        ]
        schema = {
            "columns": [
                {"name": "time", "type": date_type},
                {"name": "value", "type": "integer"},
            ]
        }
        result = to_pandas_smart(data, schema=schema)

        assert isinstance(result, pd.Series), f"Failed for type: {date_type}"
        assert isinstance(result.index, pd.DatetimeIndex), f"Failed for type: {date_type}"


def test_pandas_available():
    """Test pandas availability detection."""
    # Since we're running this test, pandas must be available
    assert _pandas_available() is True


def test_scalar_with_none_value():
    """Test scalar extraction with None value."""
    data = [{"result": None}]
    result = to_pandas_smart(data, semantic_tags=["scalar"])

    assert result is None


def test_series_name_preservation():
    """Test that series name is preserved from column name."""
    import pandas as pd

    data = [{"temperature": 20}, {"temperature": 21}, {"temperature": 22}]
    result = to_pandas_smart(data)

    assert isinstance(result, pd.Series)
    assert result.name == "temperature"


def test_timeseries_with_timestamp_values():
    """Test timeseries with actual timestamp objects."""
    import pandas as pd
    from datetime import datetime

    data = [
        {"dt": datetime(2024, 1, 1), "metric": 10},
        {"dt": datetime(2024, 1, 2), "metric": 20},
    ]
    schema = {
        "columns": [
            {"name": "dt", "type": "datetime"},
            {"name": "metric", "type": "float"},
        ]
    }
    result = to_pandas_smart(data, schema=schema)

    assert isinstance(result, pd.Series)
    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.name == "metric"


def test_multiple_semantic_tags():
    """Test handling multiple semantic tags - first match wins."""
    import pandas as pd

    data = [{"value": 100}]
    # If both scalar and vector are specified, scalar should win (it's checked first)
    result = to_pandas_smart(data, semantic_tags=["scalar", "vector"])

    assert result == 100


def test_transposed_vector():
    """Test single-row multi-column data."""
    import pandas as pd

    # Single row with multiple columns - should return DataFrame
    data = [{"col1": 1, "col2": 2, "col3": 3}]
    result = to_pandas_smart(data)

    # Without semantic tag, single row with multiple columns should be scalar (first value)
    # Actually, looking at the logic, it should return scalar since it's 1 row, 1 column check
    # But this is 1 row, 3 columns, so it should fall to DataFrame
    assert isinstance(result, pd.DataFrame)
