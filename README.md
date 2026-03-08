# Moniker Client

Python client for the Moniker Service.

## Install

```bash
pip install moniker-client
pip install moniker-client[oracle]  # with Oracle support
```

## Usage

```python
from moniker_client import read, describe

data = read("prices.equity/AAPL")           # today's data
data = read("prices.equity/AAPL@20260115")  # point-in-time
data = read("prices.equity/ALL@latest")     # all symbols

info = describe("prices.equity")            # metadata & ownership
```

## Configuration

Config file (`~/.moniker/client.yaml` or `.moniker.yaml`):

```yaml
service_url: http://localhost:8050
app_id: my-app
team: my-team
```

Or environment variables:

```bash
export MONIKER_SERVICE_URL=http://localhost:8050
export MONIKER_APP_ID=my-app
```

Or in code:

```python
from moniker_client import MonikerClient, ClientConfig

# Auto-load from config files
config = ClientConfig.load()

# Or explicit
config = ClientConfig(service_url="http://localhost:8050")

client = MonikerClient(config=config)
```

## API

| Function | Description |
|----------|-------------|
| `read(moniker)` | Fetch data |
| `describe(moniker)` | Get metadata |
| `list_children(moniker)` | List child paths |
| `lineage(moniker)` | Get ownership chain |

## Smart Pandas Conversion

When pandas is installed, the client automatically returns the most appropriate pandas object based on data structure:

```python
from moniker_client import fetch, read

# Scalar values (1 row, 1 column) → raw value
pi = fetch("constants/pi")
# Returns: 3.14159 (not a DataFrame!)

# Single column → pd.Series
prices = fetch("prices/AAPL")
# Returns: pd.Series([100, 101, 102], name="price")

# Timeseries (datetime + values) → pd.Series with DatetimeIndex
history = fetch("market/AAPL/daily")
# Returns: pd.Series with DatetimeIndex

# Multiple columns → pd.DataFrame
portfolio = fetch("portfolio/holdings")
# Returns: pd.DataFrame with all columns
```

### How It Works

**Detection hierarchy:**
1. **Semantic tags** (from catalog metadata) - highest priority
2. **Schema analysis** (column types, temporal columns)
3. **Shape heuristics** (row/column counts) - fallback

**Conversion rules:**
- Single row, single column → Scalar value
- Single column, multiple rows → `pd.Series`
- Datetime column + value column → `pd.Series` with `DatetimeIndex`
- Multiple columns → `pd.DataFrame`

### Controlling Behavior

**Disable smart conversion:**
```python
from moniker_client import MonikerClient, ClientConfig

# Disable globally
client = MonikerClient(config=ClientConfig(smart_pandas=False))
result = client.fetch("data/path")  # Returns FetchResult
df = result.to_dataframe()  # Explicit conversion

# Or use environment variable
export MONIKER_SMART_PANDAS=false
```

**Explicit conversion:**
```python
# Always get DataFrame (backward compatible)
result = client.fetch("constants/pi")
if hasattr(result, 'to_dataframe'):
    df = result.to_dataframe()  # Force DataFrame
else:
    # Smart conversion was enabled, result is already converted
    pass

# Get smart-converted object
result = client.fetch("data/path")
if hasattr(result, 'to_pandas'):
    smart = result.to_pandas()  # Smart conversion
```

**Benefits:**
- ✅ More intuitive API - get the "right" type automatically
- ✅ Less boilerplate - no need to extract scalar values
- ✅ Better timeseries support - automatic DatetimeIndex
- ✅ Backward compatible - existing code works unchanged
- ✅ Configurable - can be disabled if needed

## Adapters

The client includes built-in adapters for various data sources:

### Built-in Adapters

| Adapter | Source Type | Description |
|---------|-------------|-------------|
| **SnowflakeAdapter** | `snowflake` | Snowflake data warehouse connections |
| **OracleAdapter** | `oracle` | Oracle database connections |
| **MSSQLAdapter** | `mssql` | Microsoft SQL Server connections |
| **SQLiteAdapter** | `sqlite` | SQLite database connections |
| **RestAdapter** | `rest` | HTTP/REST API endpoints |
| **StaticAdapter** | `static` | Static/hardcoded data |
| **ExcelAdapter** | `excel` | Excel file data sources |
| **BloombergAdapter** | `bloomberg` | Bloomberg Terminal data |
| **RefinitivAdapter** | `refinitiv` | Refinitiv/Eikon data |

### Custom Adapters

Organizations can extend the library with custom adapters for proprietary data sources or to override built-in adapters with organization-specific logic (e.g., custom authentication, connection pooling).

**Quick Start:**

1. **Create an adapter configuration file:**
   ```bash
   # Copy the sample configuration
   cp .moniker.adapters.yaml.sample ~/.moniker/adapters.yaml
   ```

2. **Edit the configuration to point to your custom adapter:**
   ```yaml
   version: 1

   custom_adapters:
     # Override Oracle with custom Kerberos auth
     - source_type: oracle
       module_path: /opt/myorg/adapters/oracle_adapter.py
       class_name: CustomOracleAdapter
       enabled: true
       override: true

     # Add new SAP adapter
     - source_type: sap
       module_path: /opt/myorg/adapters/sap_adapter.py
       class_name: SAPAdapter
       enabled: true
       override: false
   ```

3. **Create your custom adapter** (outside the library repo):
   ```python
   # /opt/myorg/adapters/oracle_adapter.py
   from moniker_client.adapters.base import BaseAdapter

   class CustomOracleAdapter(BaseAdapter):
       def fetch(self, resolved, config, **kwargs):
           # Your custom implementation
           pass
   ```

4. **Use the library** - custom adapters load automatically:
   ```python
   from moniker_client import read

   # Uses CustomOracleAdapter automatically
   data = read("risk.cvar/DESK_A")
   ```

**Configuration Locations** (in precedence order):
- `~/.moniker/adapters.yaml` (user-level)
- `.moniker.adapters.yaml` (project-level)
- `MONIKER_ADAPTERS_CONFIG` environment variable

**Key Features:**
- ✅ **Complete separation**: Custom adapters live outside the library repository
- ✅ **Auto-discovery**: Adapters load automatically at import time
- ✅ **Override support**: Replace built-in adapters with custom implementations
- ✅ **Graceful fallback**: Missing adapters don't break library installation
- ✅ **No blocking**: Library works with built-in adapters if no config exists

For complete examples and configuration options, see [`.moniker.adapters.yaml.sample`](.moniker.adapters.yaml.sample).
