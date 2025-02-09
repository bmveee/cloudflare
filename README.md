# Cloudflare DNS Updater

A Python tool to automatically update Cloudflare DNS records with your current IP address. Supports multiple domains and API tokens.

## Features

- Updates multiple DNS records across different domains
- Supports multiple Cloudflare API tokens
- Caches IP address to minimize API calls
- Dry run mode for testing
- Debug logging support
- Environment variable templating in configuration

## Installation

1. Clone the repository:
```bash
git clone https://github.com/bmveee/cloudflare
cd cloudflare
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

1. Copy the example configuration files:
```bash
cp .env.sample .env
cp cf_configs.yaml.example cf_configs.yaml
```

2. Update `.env` with your credentials:
```
CLOUDFLARE_PERSONAL_TOKEN=your_token_here
CLOUDFLARE_PERSONAL_ACCNT=your_account_here
CLOUDFLARE_CONF=cf_configs.yaml
```

3. Configure your domains in `cf_configs.yaml`:
```yaml
auth_tokens:
  - token: ${CLOUDFLARE_PERSONAL_TOKEN}
    desc: "DNS zones for account ${CLOUDFLARE_PERSONAL_ACCNT}"
    domains:
      - zone_name: "example.com"
        records:
          - name: "subdomain"
            type: "A"
            proxied: true
            ttl: 300
```

## Usage

Basic usage:
```bash
python update_cloudflare.py
```

With debug output:
```bash
python update_cloudflare.py -d
```

Dry run mode:
```bash
python update_cloudflare.py --dry-run
```

Custom config file:
```bash
python update_cloudflare.py -c custom_config.yaml
```

## Command Line Arguments

- `-d, --debug`: Enable debug logging
- `--dry-run`: Show what would be done without making changes
- `-c, --config`: Specify custom config file path

## Cache Management

The script maintains a cache file (`cf_cache.json`) to track the last known IP address and minimize API calls. The cache is updated when:
- The script runs for the first time
- Your IP address changes
- DNS records are updated

## Notes

- Requires Python 3.6+
- API tokens must have DNS edit permissions
- Respects Cloudflare API rate limits
- Supports IPv4 addresses only

## Error Handling

The script includes comprehensive error handling and logging:
- API request failures
- Configuration errors
- Cache file corruption
- DNS record not found
- Zone not found

