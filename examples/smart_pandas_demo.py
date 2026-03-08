"""
Demo script showing smart pandas conversion in action.

This demonstrates how the moniker client automatically returns
the most appropriate pandas object based on data structure.
"""

from moniker_client import MonikerClient, ClientConfig
from moniker_client.client import FetchResult


def demo_smart_conversion():
    """Demonstrate smart pandas conversion."""
    print("=" * 70)
    print("Smart Pandas Conversion Demo")
    print("=" * 70)

    # Create client with smart_pandas enabled (default)
    client = MonikerClient(config=ClientConfig(smart_pandas=True, report_telemetry=False))

    print("\n1. SCALAR VALUE (1 row, 1 column)")
    print("-" * 70)
    # Mock a scalar result
    result = FetchResult(
        moniker="moniker://constants/pi",
        path="constants/pi",
        source_type="static",
        row_count=1,
        columns=["value"],
        data=[{"value": 3.14159}],
        semantic_tags=["scalar"],
    )
    converted = result.to_pandas()
    print(f"Data: {result.data}")
    print(f"Smart conversion → {type(converted).__name__}: {converted}")
    print(f"✓ Returns scalar value directly, not DataFrame")

    print("\n2. VECTOR (single column)")
    print("-" * 70)
    result = FetchResult(
        moniker="moniker://prices/AAPL",
        path="prices/AAPL",
        source_type="sqlite",
        row_count=5,
        columns=["price"],
        data=[
            {"price": 150.25},
            {"price": 151.30},
            {"price": 149.80},
            {"price": 152.10},
            {"price": 151.75},
        ],
        semantic_tags=["vector"],
    )
    converted = result.to_pandas()
    print(f"Data: {len(result.data)} rows, {len(result.columns)} column")
    print(f"Smart conversion → {type(converted).__name__}:")
    print(converted)
    print(f"✓ Returns pd.Series with name='{converted.name}'")

    print("\n3. TIMESERIES (datetime + values)")
    print("-" * 70)
    result = FetchResult(
        moniker="moniker://market/AAPL/history",
        path="market/AAPL/history",
        source_type="sqlite",
        row_count=5,
        columns=["date", "close"],
        data=[
            {"date": "2024-01-01", "close": 150.25},
            {"date": "2024-01-02", "close": 151.30},
            {"date": "2024-01-03", "close": 149.80},
            {"date": "2024-01-04", "close": 152.10},
            {"date": "2024-01-05", "close": 151.75},
        ],
        semantic_tags=["timeseries"],
        schema={
            "columns": [
                {"name": "date", "type": "datetime"},
                {"name": "close", "type": "float"},
            ]
        },
    )
    converted = result.to_pandas()
    print(f"Data: {len(result.data)} rows, {len(result.columns)} columns")
    print(f"Smart conversion → {type(converted).__name__} with {type(converted.index).__name__}:")
    print(converted)
    print(f"✓ Returns pd.Series with DatetimeIndex")

    print("\n4. DATAFRAME (multiple columns)")
    print("-" * 70)
    result = FetchResult(
        moniker="moniker://portfolio/holdings",
        path="portfolio/holdings",
        source_type="sqlite",
        row_count=3,
        columns=["symbol", "quantity", "price", "value"],
        data=[
            {"symbol": "AAPL", "quantity": 100, "price": 150.25, "value": 15025.00},
            {"symbol": "GOOGL", "quantity": 50, "price": 2800.50, "value": 140025.00},
            {"symbol": "MSFT", "quantity": 200, "price": 380.75, "value": 76150.00},
        ],
    )
    converted = result.to_pandas()
    print(f"Data: {len(result.data)} rows, {len(result.columns)} columns")
    print(f"Smart conversion → {type(converted).__name__}:")
    print(converted)
    print(f"✓ Returns pd.DataFrame for multi-column data")

    print("\n5. BACKWARD COMPATIBILITY")
    print("-" * 70)
    result = FetchResult(
        moniker="moniker://constants/pi",
        path="constants/pi",
        source_type="static",
        row_count=1,
        columns=["value"],
        data=[{"value": 3.14159}],
        semantic_tags=["scalar"],
    )
    # Old code using to_dataframe() still works
    df = result.to_dataframe()
    print(f"result.to_dataframe() → {type(df).__name__}:")
    print(df)
    print(f"✓ to_dataframe() always returns DataFrame (backward compatible)")

    print("\n6. DISABLING SMART CONVERSION")
    print("-" * 70)
    client_no_smart = MonikerClient(config=ClientConfig(smart_pandas=False, report_telemetry=False))
    print(f"ClientConfig(smart_pandas=False)")
    print(f"✓ When disabled, returns FetchResult object")
    print(f"✓ User can call .to_dataframe() or .to_pandas() explicitly")

    print("\n" + "=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    demo_smart_conversion()
