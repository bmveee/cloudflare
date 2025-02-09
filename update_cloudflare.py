import argparse
from dotenv import load_dotenv
import os

from cf_updater import Status, CloudflareUpdater
from util import setup_logging, load_yaml_with_defaults, get_current_ip

def parse_args():
    parser = argparse.ArgumentParser(
        description="Update Cloudflare DNS records with current IP"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help="Enable debug logger", default=False
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
        default=False,
    )
    parser.add_argument(
        "--config",
        help="Path to config file (default: value from CLOUDFLARE_CONF env var)",
        default=os.getenv("CLOUDFLARE_CONF"),
    )
    parser.add_argument(
        "--cache",
        help="Path to cache file (default: value from CLOUDFLARE_CACHE env var or cf_cache.json)",
        default=os.getenv("CLOUDFLARE_CACHE", "cf_cache.json"),
    )
    parser.add_argument(
        "--log-level",
        help="Log level of debugging, default = 0",
        default=0,
    )

    return parser.parse_args()


def main():
    load_dotenv()
    args = parse_args()
    logger = setup_logging(args.debug)

    if args.debug:
        logger.debug("Environment variables:")
        logger.debug(
            f"CLOUDFLARE_CONF: {os.environ.get('CLOUDFLARE_CONF', 'not set')}"
        )
        logger.debug(f"Config file path: {args.config}")

    config = load_yaml_with_defaults(args.config, logger, log_level=args.log_level)
    current_ip = get_current_ip()
    logger.info(f'Current IPv4 Address: {current_ip}')

    updater = CloudflareUpdater(cache_file=args.cache, dry_run=args.dry_run, logger=logger)

    try:
        updater.update_all_records(config["auth_tokens"], current_ip)
        logger.info(f"{Status.Success} Update finished")
    except Exception as e:
        logger.error(f"[{Status.Failure}] Failed to update records: {str(e)}")


if __name__ == "__main__":
    main()
