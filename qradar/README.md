# QRadar Collector for OpenBAS/OpenAEV

A barebones collector that integrates IBM QRadar SIEM with OpenBAS/OpenAEV platform for security detection validation.

## 📋 Overview

This collector validates security detection expectations by querying your QRadar SIEM for matching offenses. It connects to both OpenBAS (to fetch expectations) and QRadar (to fetch security offenses), then matches them based on IP addresses.

**Note**: This is a barebones implementation with minimal features - perfect for getting started quickly.

## ✨ Features

- **Detection Validation**: Queries QRadar offenses to verify security detections
- **IP-based Matching**: Supports source and destination IPv4 address matching
- **Time Range Filtering**: Configurable time windows for offense searches
- **Automatic Updates**: Updates OpenBAS with detection results (Detected / Not Detected)
- **Simple Configuration**: YAML or environment variable configuration

## 🔧 Requirements

- **OpenBAS/OpenAEV Platform** - Running instance with API access
- **IBM QRadar SIEM** - Version 7.3+ with REST API enabled
- **Python 3.11+** - For running the collector
- **QRadar SEC Token** - API authentication token
- **Network Access** - Collector must reach both OpenBAS and QRadar

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd qradar
poetry install -E prod --with dev
```

### 2. Configure the Collector

Copy the sample config and edit it:

```bash
cp src/config.yml.sample src/config.yml
vim src/config.yml
```

**Required settings:**

```yaml
openaev:
  url: "https://your-openbas.com"
  token: "your-openbas-token"

collector:
  id: "qradar--<generate-uuid-here>"

qradar:
  base_url: "https://10.10.0.255"      # Your QRadar IP
  sec_token: "your-qradar-sec-token"
```

### 3. Get QRadar SEC Token

1. Log into QRadar Console
2. Navigate to **Admin → Authorized Services**
3. Click **"Create New Token"**
4. Copy the generated token to your config

### 4. Run the Collector

```bash
poetry run python -m src
```

Or install and run:

```bash
poetry install -E prod
QRadarCollector
```

## ⚙️ Configuration

### Configuration File (`src/config.yml`)

The collector supports three configuration sources (in priority order):
1. **Environment variables** (highest priority)
2. **YAML config file** (`src/config.yml`)
3. **Default values** (fallback)

### OpenBAS Settings

| Parameter | Environment Variable | Description | Required |
|-----------|---------------------|-------------|----------|
| `openaev.url` | `OPENAEV_URL` | OpenBAS platform URL | Yes |
| `openaev.token` | `OPENAEV_TOKEN` | OpenBAS API token | Yes |

### Collector Settings

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `collector.id` | `COLLECTOR_ID` | `qradar--00000...` | Unique collector UUID |
| `collector.name` | `COLLECTOR_NAME` | `QRadar Collector` | Display name |
| `collector.period` | `COLLECTOR_PERIOD` | `PT5M` | Collection interval (5 min) |
| `collector.log_level` | `COLLECTOR_LOG_LEVEL` | `info` | Logging level |

### QRadar Settings

| Parameter | Environment Variable | Default | Description |
|-----------|---------------------|---------|-------------|
| `qradar.base_url` | `QRADAR_BASE_URL` | `https://10.10.0.255` | QRadar Console URL |
| `qradar.sec_token` | `QRADAR_SEC_TOKEN` | - | SEC API token |
| `qradar.verify_ssl` | `QRADAR_VERIFY_SSL` | `false` | Verify SSL certificates |
| `qradar.time_window` | `QRADAR_TIME_WINDOW` | `PT1H` | Search time window (1 hour) |
| `qradar.max_retry` | `QRADAR_MAX_RETRY` | `3` | Retry attempts |
| `qradar.offset` | `QRADAR_OFFSET` | `PT30S` | Retry delay (30 seconds) |

### Environment Variable Example

```bash
export OPENAEV_URL="https://openbas.example.com"
export OPENAEV_TOKEN="abc123..."
export COLLECTOR_ID="qradar--12345678-1234-1234-1234-123456789abc"
export QRADAR_BASE_URL="https://10.10.0.255"
export QRADAR_SEC_TOKEN="xyz789..."
export QRADAR_VERIFY_SSL="false"
```

## 🎯 Supported Signatures

The barebones collector supports these signature types:

- ✅ `source_ipv4_address` - Source IP addresses
- ✅ `target_ipv4_address` - Destination IP addresses
- ✅ `start_date` - Start time for searches
- ✅ `end_date` - End time for searches

**Not supported in barebones version:**
- ❌ `source_ipv6_address` (can be added later)
- ❌ `target_ipv6_address` (can be added later)
- ❌ `parent_process_name` (QRadar doesn't track this well)
- ❌ Prevention expectations (QRadar is detection-only SIEM)

## 🔄 How It Works

### Processing Flow

1. **Fetch Expectations** - Collector queries OpenBAS API for pending expectations
2. **Extract Signatures** - Parses IP addresses and time ranges from expectations
3. **Query QRadar** - Calls QRadar `/api/siem/offenses` endpoint with filters
4. **Convert Data** - Transforms QRadar offenses to OpenBAS format
5. **Match** - Uses DetectionHelper to match offenses against expectations
6. **Update OpenBAS** - Marks expectations as "Detected" or "Not Detected"

### Example Workflow

```
OpenBAS Expectation:
  - source_ipv4_address: 192.168.1.100
  - target_ipv4_address: 10.0.0.50

       ↓

QRadar API Query:
  GET /api/siem/offenses?filter=offense_source='192.168.1.100' or local_destination_ip='10.0.0.50'

       ↓

QRadar Response:
  [
    {
      "id": 123,
      "offense_source": "192.168.1.100",
      "local_destination_ip": "10.0.0.50",
      "description": "Suspicious Activity Detected"
    }
  ]

       ↓

Result: DETECTED ✅
```

## 🐛 Troubleshooting

### No Offenses Found

**Problem**: Collector finds no matching offenses

**Solutions**:
- Check that QRadar has offenses in the time window
- Verify IP addresses match exactly
- Increase `time_window` in config (e.g., `PT24H` for 24 hours)
- Check QRadar Console manually for offenses

### Authentication Errors

**Problem**: `401 Unauthorized` errors

**Solutions**:
- Verify SEC token is correct
- Token might have expired - regenerate in QRadar Console
- Check token has necessary API permissions

### Connection Errors

**Problem**: Cannot connect to QRadar

**Solutions**:
- Verify `base_url` is correct (include `https://`)
- Check network connectivity: `curl -k https://10.10.0.255/api/help/versions`
- If SSL errors, set `verify_ssl: false` in config
- Check firewall rules allow connections to QRadar

### SSL Certificate Errors

**Problem**: SSL verification failures

**Solutions**:
- Set `verify_ssl: false` for internal QRadar instances
- For production, install proper SSL certificates on QRadar

## 📁 Project Structure

```
qradar/
├── pyproject.toml              # Poetry dependencies
├── README.md                   # This file
├── src/
│   ├── __main__.py            # Entry point
│   ├── config.yml.sample      # Sample configuration
│   ├── collector/
│   │   ├── collector.py       # Main collector orchestrator
│   │   ├── exception.py       # Collector exceptions
│   │   └── models.py          # Result models
│   ├── models/
│   │   └── configs/
│   │       ├── config_loader.py    # Config loader
│   │       └── qradar_configs.py   # QRadar settings
│   └── services/
│       ├── client_api.py      # QRadar REST API client
│       ├── converter.py       # Data format converter
│       ├── exception.py       # Service exceptions
│       ├── expectation_service.py  # Business logic
│       └── models.py          # QRadar data models
```

## 🔑 QRadar API Details

### Endpoint Used

```
GET /api/siem/offenses
```

### Required Permissions

Your QRadar SEC token needs:
- Read access to offenses
- API access enabled

### Sample API Call

```bash
curl -k -X GET \
  'https://10.10.0.255/api/siem/offenses?filter=start_time%20%3E%201234567890' \
  -H 'SEC: your-token-here' \
  -H 'Accept: application/json' \
  -H 'Version: 14.0'
```

## 📝 Logging

The collector provides logging at multiple levels:

- **ERROR**: Critical failures
- **WARN**: Recoverable issues
- **INFO**: Processing progress (default)
- **DEBUG**: Detailed API calls and matching logic

Set log level in config:
```yaml
collector:
  log_level: "debug"  # For troubleshooting
```

## 🚧 Limitations (Barebones Version)

- **IPv4 only** - No IPv6 support
- **No trace service** - No audit trail back to QRadar
- **Simple retry** - Basic retry logic only
- **Detection only** - Prevention expectations marked as invalid
- **No parent process** - QRadar doesn't provide this data
- **Individual updates** - No bulk update optimization

## 🛠️ Future Enhancements

Potential additions for full-featured version:
- IPv6 address support
- Trace service with QRadar console links
- Advanced retry logic with exponential backoff
- Bulk expectation updates
- AQL query support for complex searches
- Docker deployment
- Comprehensive test suite

## 📜 License

This project follows the OpenAEV project license.

## 🤝 Contributing

This is a barebones collector - contributions welcome to add features!

## 📞 Support

- Check QRadar API documentation: `/api/doc` on your QRadar instance
- OpenBAS documentation: https://docs.openbas.io
- Check logs with `log_level: debug` for troubleshooting
