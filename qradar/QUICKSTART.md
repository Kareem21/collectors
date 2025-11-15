# QRadar Collector - Quick Start Guide

Get your QRadar collector running in 5 minutes!

## Step 1: Install Dependencies

```bash
cd /home/user/collectors/qradar
poetry install -E prod
```

## Step 2: Create Configuration

```bash
cp src/config.yml.sample src/config.yml
nano src/config.yml  # or vim, vi, etc.
```

## Step 3: Fill in Required Settings

Edit `src/config.yml` with your actual values:

```yaml
openaev:
  url: "https://your-openbas-instance.com"
  token: "paste-your-openbas-token-here"

collector:
  id: "qradar--12345678-1234-1234-1234-123456789abc"  # Generate a UUID

qradar:
  base_url: "https://10.10.0.255"         # Your QRadar IP
  sec_token: "paste-your-qradar-token"    # Get from QRadar Console
  verify_ssl: false                        # Usually false for internal QRadar
```

### How to Get QRadar SEC Token

1. Open QRadar Console in browser
2. Click **Admin** (top right)
3. Go to **Authorized Services**
4. Click **"Create New Token"**
5. Copy the token string
6. Paste into `sec_token` in config.yml

### How to Generate Collector UUID

Online: Visit https://www.uuidgenerator.net/version4

Or use Python:
```bash
python3 -c "import uuid; print(f'qradar--{uuid.uuid4()}')"
```

## Step 4: Run the Collector

```bash
poetry run python -m src
```

You should see:
```
2025-11-15 12:00:00 - INFO - [Main] Starting QRadar collector...
2025-11-15 12:00:01 - INFO - [QRadarCollector] QRadar Collector initialized successfully
2025-11-15 12:00:02 - INFO - [QRadarCollector] Collector setup completed successfully
...
```

## Step 5: Verify It's Working

Check the logs for:
- ✅ "Collector initialized successfully"
- ✅ "Starting processing cycle..."
- ✅ "Found X expectations to process"

If you see errors:
- **401 Unauthorized**: Check your QRadar SEC token
- **Connection refused**: Check your QRadar base_url
- **SSL errors**: Set `verify_ssl: false`

## Testing with a Sample Expectation

Create an expectation in OpenBAS with:
- **Source IP**: An IP from a real QRadar offense
- **Target IP**: A destination IP from a real offense

The collector should:
1. Fetch the expectation
2. Query QRadar for matching offenses
3. Update the expectation as "Detected" if found

## Stopping the Collector

Press `Ctrl+C` to stop gracefully.

## Troubleshooting

### "No expectations to process"
- Create an expectation in OpenBAS first
- Verify the collector ID matches in OpenBAS

### "No offenses found"
- Check QRadar has offenses in the time window (default: last 1 hour)
- Try increasing `time_window: "PT24H"` for 24 hours

### "Connection refused"
- Verify QRadar is accessible: `ping 10.10.0.255`
- Check QRadar URL includes `https://`
- Verify firewall allows connections

## Next Steps

Once running successfully:
1. Set `log_level: "debug"` to see detailed operations
2. Adjust `period` to change collection frequency (e.g., `PT1M` for 1 minute)
3. Monitor OpenBAS to see detection results

## File Summary

Each file has a 10-line comment at the top explaining its purpose:

- `src/__main__.py` - Entry point
- `src/collector/collector.py` - Main orchestrator
- `src/services/expectation_service.py` - Business logic
- `src/services/client_api.py` - QRadar API calls
- `src/services/converter.py` - Data transformation
- `src/models/configs/config_loader.py` - Configuration management
- `src/models/configs/qradar_configs.py` - QRadar settings

Happy collecting! 🚀
