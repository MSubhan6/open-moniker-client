"""Integration tests for smart pandas conversion."""

from __future__ import annotations

import pytest
from unittest.mock import Mock, patch, MagicMock

from moniker_client import MonikerClient
from moniker_client.config import ClientConfig
from moniker_client.client import FetchResult, MetadataResult
from moniker_client.pandas_utils import _pandas_available


pytestmark = pytest.mark.skipif(not _pandas_available(), reason="pandas not installed")


@pytest.fixture
def mock_metadata_response():
    """Mock metadata response."""
    def _make_metadata(semantic_tags=None, schema=None):
        return MetadataResult(
            moniker="moniker://test/path",
            path="test/path",
            semantic_tags=semantic_tags or [],
            schema=schema,
        )
    return _make_metadata


@pytest.fixture
def mock_client():
    """Create a mock client for testing."""
    client = MonikerClient(config=ClientConfig(smart_pandas=True, report_telemetry=False))
    return client


def test_fetch_result_to_pandas_scalar(mock_metadata_response):
    """Test FetchResult.to_pandas() returns scalar."""
    import pandas as pd

    result = FetchResult(
        moniker="moniker://constants/pi",
        path="constants/pi",
        source_type="static",
        row_count=1,
        columns=["value"],
        data=[{"value": 3.14159}],
        semantic_tags=["scalar"],
    )

    output = result.to_pandas()
    assert output == 3.14159
    assert not isinstance(output, (pd.Series, pd.DataFrame))


def test_fetch_result_to_pandas_series(mock_metadata_response):
    """Test FetchResult.to_pandas() returns Series."""
    import pandas as pd

    result = FetchResult(
        moniker="moniker://prices/AAPL",
        path="prices/AAPL",
        source_type="sqlite",
        row_count=3,
        columns=["price"],
        data=[{"price": 100}, {"price": 101}, {"price": 102}],
        semantic_tags=["vector"],
    )

    output = result.to_pandas()
    assert isinstance(output, pd.Series)
    assert output.name == "price"
    assert len(output) == 3


def test_fetch_result_to_pandas_timeseries(mock_metadata_response):
    """Test FetchResult.to_pandas() returns Series with DatetimeIndex."""
    import pandas as pd

    result = FetchResult(
        moniker="moniker://market/AAPL/history",
        path="market/AAPL/history",
        source_type="sqlite",
        row_count=2,
        columns=["date", "close"],
        data=[
            {"date": "2024-01-01", "close": 150.25},
            {"date": "2024-01-02", "close": 151.30},
        ],
        semantic_tags=["timeseries"],
        schema={
            "columns": [
                {"name": "date", "type": "datetime"},
                {"name": "close", "type": "float"},
            ]
        },
    )

    output = result.to_pandas()
    assert isinstance(output, pd.Series)
    assert isinstance(output.index, pd.DatetimeIndex)
    assert output.name == "close"


def test_fetch_result_to_pandas_dataframe(mock_metadata_response):
    """Test FetchResult.to_pandas() returns DataFrame."""
    import pandas as pd

    result = FetchResult(
        moniker="moniker://portfolio/holdings",
        path="portfolio/holdings",
        source_type="sqlite",
        row_count=2,
        columns=["symbol", "price", "volume"],
        data=[
            {"symbol": "AAPL", "price": 150, "volume": 1000},
            {"symbol": "GOOGL", "price": 2800, "volume": 500},
        ],
    )

    output = result.to_pandas()
    assert isinstance(output, pd.DataFrame)
    assert len(output) == 2
    assert list(output.columns) == ["symbol", "price", "volume"]


def test_fetch_result_to_dataframe_backward_compat(mock_metadata_response):
    """Test FetchResult.to_dataframe() always returns DataFrame."""
    import pandas as pd

    # Even with scalar tag, to_dataframe() should return DataFrame
    result = FetchResult(
        moniker="moniker://constants/pi",
        path="constants/pi",
        source_type="static",
        row_count=1,
        columns=["value"],
        data=[{"value": 3.14159}],
        semantic_tags=["scalar"],
    )

    output = result.to_dataframe()
    assert isinstance(output, pd.DataFrame)
    assert len(output) == 1


def test_client_fetch_smart_conversion_enabled():
    """Test client.fetch() with smart_pandas=True."""
    import pandas as pd

    client = MonikerClient(config=ClientConfig(smart_pandas=True, report_telemetry=False))

    # Mock the HTTP response
    with patch('httpx.Client') as mock_httpx:
        # Mock fetch response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "moniker": "moniker://constants/pi",
            "path": "constants/pi",
            "source_type": "static",
            "row_count": 1,
            "columns": ["value"],
            "data": [{"value": 3.14159}],
        }

        # Mock metadata response
        mock_meta_response = Mock()
        mock_meta_response.status_code = 200
        mock_meta_response.json.return_value = {
            "moniker": "moniker://constants/pi",
            "path": "constants/pi",
            "semantic_tags": ["scalar"],
            "schema": None,
        }

        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = [mock_response, mock_meta_response]
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_httpx.return_value = mock_client_instance

        result = client.fetch("constants/pi")

        # Should return scalar value
        assert result == 3.14159
        assert not isinstance(result, (pd.Series, pd.DataFrame))


def test_client_fetch_smart_conversion_disabled():
    """Test client.fetch() with smart_pandas=False."""
    client = MonikerClient(config=ClientConfig(smart_pandas=False, report_telemetry=False))

    # Mock the HTTP response
    with patch('httpx.Client') as mock_httpx:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "moniker": "moniker://constants/pi",
            "path": "constants/pi",
            "source_type": "static",
            "row_count": 1,
            "columns": ["value"],
            "data": [{"value": 3.14159}],
        }

        mock_client_instance = MagicMock()
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_httpx.return_value = mock_client_instance

        result = client.fetch("constants/pi")

        # Should return FetchResult
        assert isinstance(result, FetchResult)
        assert result.data == [{"value": 3.14159}]


def test_client_read_smart_conversion():
    """Test client.read() with smart conversion."""
    import pandas as pd

    client = MonikerClient(config=ClientConfig(smart_pandas=True, report_telemetry=False))

    # Mock resolve and adapter
    with patch.object(client, '_resolve') as mock_resolve, \
         patch.object(client, 'metadata') as mock_metadata, \
         patch('moniker_client.client.get_adapter') as mock_get_adapter:

        # Mock resolved source
        from moniker_client.client import ResolvedSource
        mock_resolve.return_value = ResolvedSource(
            moniker="moniker://prices/AAPL",
            path="prices/AAPL",
            source_type="static",
            connection={},
            query=None,
            params={},
            schema_info=None,
            read_only=True,
            ownership={},
            binding_path="prices/AAPL",
            sub_path=None,
        )

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.fetch.return_value = [
            {"price": 100},
            {"price": 101},
            {"price": 102},
        ]
        mock_get_adapter.return_value = mock_adapter

        # Mock metadata
        mock_metadata.return_value = MetadataResult(
            moniker="moniker://prices/AAPL",
            path="prices/AAPL",
            semantic_tags=["vector"],
            schema=None,
        )

        result = client.read("prices/AAPL")

        # Should return Series
        assert isinstance(result, pd.Series)
        assert result.name == "price"
        assert len(result) == 3


def test_client_read_smart_conversion_disabled():
    """Test client.read() with smart_pandas=False."""
    client = MonikerClient(config=ClientConfig(smart_pandas=False, report_telemetry=False))

    # Mock resolve and adapter
    with patch.object(client, '_resolve') as mock_resolve, \
         patch('moniker_client.client.get_adapter') as mock_get_adapter:

        # Mock resolved source
        from moniker_client.client import ResolvedSource
        mock_resolve.return_value = ResolvedSource(
            moniker="moniker://prices/AAPL",
            path="prices/AAPL",
            source_type="static",
            connection={},
            query=None,
            params={},
            schema_info=None,
            read_only=True,
            ownership={},
            binding_path="prices/AAPL",
            sub_path=None,
        )

        # Mock adapter
        mock_adapter = Mock()
        mock_adapter.fetch.return_value = [
            {"price": 100},
            {"price": 101},
            {"price": 102},
        ]
        mock_get_adapter.return_value = mock_adapter

        result = client.read("prices/AAPL")

        # Should return raw list of dicts
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == {"price": 100}


def test_config_smart_pandas_default():
    """Test that smart_pandas defaults to True when pandas is available."""
    config = ClientConfig()
    assert config.smart_pandas is True


def test_config_smart_pandas_explicit():
    """Test explicit smart_pandas setting."""
    config = ClientConfig(smart_pandas=False)
    assert config.smart_pandas is False


def test_fetch_with_metadata_fetch_failure():
    """Test fetch continues gracefully when metadata fetch fails."""
    import pandas as pd

    client = MonikerClient(config=ClientConfig(smart_pandas=True, report_telemetry=False))

    with patch('httpx.Client') as mock_httpx:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "moniker": "moniker://test/data",
            "path": "test/data",
            "source_type": "static",
            "row_count": 2,
            "columns": ["col1", "col2"],
            "data": [{"col1": 1, "col2": 2}, {"col1": 3, "col2": 4}],
        }

        # Metadata fetch fails
        mock_meta_response = Mock()
        mock_meta_response.status_code = 500
        mock_meta_response.raise_for_status.side_effect = Exception("Server error")

        mock_client_instance = MagicMock()
        mock_client_instance.get.side_effect = [mock_response, mock_meta_response]
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_httpx.return_value = mock_client_instance

        result = client.fetch("test/data")

        # Should still work, falling back to shape heuristics
        assert isinstance(result, pd.DataFrame)


def test_empty_data_returns_empty_dataframe():
    """Test that empty data returns empty DataFrame."""
    import pandas as pd

    result = FetchResult(
        moniker="moniker://empty/data",
        path="empty/data",
        source_type="static",
        row_count=0,
        columns=[],
        data=[],
    )

    output = result.to_pandas()
    assert isinstance(output, pd.DataFrame)
    assert len(output) == 0
