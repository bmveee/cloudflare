import json
import os
import requests
from requests.exceptions import RequestException, Timeout
from util import setup_logging, Logger

class Symbols:
    CHECK_MARK = "\u2713"
    CROSS_MARK = "\u274c"

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    RESET = "\033[0m"

class Status:
    Failure = f"[{Colors.RED}{Symbols.CROSS_MARK}{Colors.RESET}]"
    Success = f"[{Colors.GREEN}{Symbols.CHECK_MARK}{Colors.RESET}]"


class CloudflareUpdater:
    def __init__(self, cache_file: str = "cf_cache.json", dry_run: bool = False, logger:Logger = None):
        self.dry_run = dry_run
        self.base_url = "https://api.cloudflare.com/client/v4"
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.logger = logger if logger else setup_logging()

    def _get_headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _save_cache(self) -> None:
        """Save cache to file"""
        try:
            cache_dir = os.path.dirname(self.cache_file)
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self.cache, f, indent=2)
            self.logger.info(f"{Status.Success} Cache saved to {self.cache_file}")
        except IOError as e:
            self.logger.error(f"{Status.Failure} Failed to save cache: {str(e)}")

    def _load_cache(self) -> dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.warning(
                    f"{Status.Failure} Cache file corrupted, creating new cache"
                )
        return {"last_ip": None, "tokens": {}}

    def _ip_has_changed(self, current_ip: str) -> bool:
        return self.cache["last_ip"] != current_ip

    def _make_request(
        self, method: str, url: str, headers: dict, json_data: dict = None
    ) -> requests.Response:
        try:
            response = requests.request(
                method=method, url=url, headers=headers, json=json_data, timeout=30
            )
            response.raise_for_status()
            return response
        except Timeout:
            self.logger.error(f"{Status.Failure} Request timed out: {url}")
            raise
        except RequestException as e:
            self.logger.error(f"{Status.Failure} Request failed: {str(e)}")
            raise

    def update_all_records(self, auth_tokens: list, current_ip: str) -> None:
        first_run = self.cache["last_ip"] is None
        ip_changed = self._ip_has_changed(current_ip)
        updates_made = False

        if first_run:
            self.logger.info(
                f"{Status.Success} First run detected, will save initial state"
            )
        elif ip_changed:
            self.logger.info(
                f"{Status.Success} IP changed from {self.cache['last_ip']} to {current_ip}"
            )
        else:
            self.logger.info(f"{Status.Success} IP {current_ip} hasn't changed")

        for auth_config in auth_tokens:
            token = auth_config["token"]
            headers = self._get_headers(token)

            try:
                # Fetch zones for this token
                zones_response = self._make_request(
                    method="GET", url=f"{self.base_url}/zones", headers=headers
                )

                zones_data = {
                    zone["name"]: zone["id"] for zone in zones_response.json()["result"]
                }

                # Update each domain under this token
                for domain in auth_config["domains"]:
                    if self._update_domain(domain, zones_data, headers, current_ip):
                        updates_made = True

            except RequestException as e:
                self.logger.error(
                    f"{Status.Failure} Failed to update zones for token {auth_config['desc']}: {str(e)}"
                )
                continue

        # Save cache if any updates were made or if it's the first run or if the IP has changed
        if first_run or ip_changed or updates_made:
            self.cache["last_ip"] = current_ip
            self._save_cache()

    def _update_domain(
        self, domain: dict, zones_data: dict, headers: dict, current_ip: str
    ) -> bool:
        zone_name = domain["zone_name"]
        zone_id = zones_data.get(zone_name)

        if not zone_id:
            self.logger.error(f"{Status.Failure} Zone {zone_name} not found")
            return False

        try:
            dns_records_url = f"{self.base_url}/zones/{zone_id}/dns_records"
            dns_response = self._make_request(
                method="GET", url=dns_records_url, headers=headers
            )

            records_data = {
                record["name"]: {"id": record["id"], "content": record["content"]}
                for record in dns_response.json()["result"]
            }

            updates_made = False
            for record in domain["records"]:
                if self._update_record(
                    record, zone_id, zone_name, records_data, headers, current_ip
                ):
                    updates_made = True

            return updates_made

        except RequestException as e:
            self.logger.error(
                f"{Status.Failure} Failed to update domain {zone_name}: {str(e)}"
            )
            return False

    def _update_record(
        self,
        record: dict,
        zone_id: str,
        zone_name: str,
        records_data: dict,
        headers: dict,
        current_ip: str,
    ) -> bool:
        try:
            record_fqdn = f"{record['name']}.{zone_name}"
            cached_record = records_data.get(record_fqdn)

            if not cached_record:
                self.logger.error(f"{Status.Failure} Record {record_fqdn} not found")
                return False

            if cached_record["content"] == current_ip:
                self.logger.info(
                    f"{Status.Success} Record {record_fqdn} already up to date"
                )
                return False

            if not self.dry_run:
                update_url = (
                    f"{self.base_url}/zones/{zone_id}/dns_records/{cached_record['id']}"
                )
                update_data = {
                    "type": record["type"],
                    "name": record["name"],
                    "content": current_ip,
                    "proxied": record["proxied"],
                    "ttl": record["ttl"],
                }

                self._make_request(
                    method="PUT", url=update_url, headers=headers, json_data=update_data
                )
                self.logger.info(f"{Status.Success} Updated {record_fqdn} to {current_ip}")
                return True
            else:
                self.logger.info(
                    f"{Status.Success} Dry run: Would update {record_fqdn} to {current_ip}"
                )
                return True

        except RequestException as e:
            self.logger.error(f"{Status.Failure} Failed to update {record_fqdn}: {str(e)}")
            return False
