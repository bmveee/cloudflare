# util.py
from logging import Logger
import logging
import os
import re
import requests
import yaml

def setup_logging(debug_mode: bool = False) -> Logger:
    """Setup and return a configured logger instance"""
    logger = logging.getLogger("cloudflare_updater")
    logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(filename)s:%(lineno)d | %(funcName)s() | %(levelname)s | %(message)s",
        datefmt="%Y%m%d-%H:%M:%S.%f",
    )

    # Add formatter to handler
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    return logger

if __name__ == '__main__':
  pass

def load_yaml_with_defaults(yaml_path, logger: Logger, log_level: int =0):
    pattern = re.compile(r"\${([A-Za-z0-9_-]+)(?::([^}]+))?}")

    def env_constructor(loader, node):
        value = loader.construct_scalar(node)
        if log_level > 0:
          logger.debug(f"Processing value: {value}")

        for match in pattern.finditer(value):
            env_var, default = match.groups()
            env_value = os.environ.get(env_var, default)
            logger.debug(f"Found variable: {env_var}, value: {env_value}")

            if env_value is not None:
                old_value = value
                value = value.replace(match.group(0), env_value)
                if log_level > 0:
                  logger.debug(f"Replacing {match.group(0)} with {env_value}")
                  logger.debug(f"Value changed from '{old_value}' to '{value}'")
        return value

    # Add constructor for all scalars
    yaml.add_constructor("tag:yaml.org,2002:str", env_constructor, yaml.SafeLoader)

    with open(yaml_path, "r") as file:
        return yaml.safe_load(file)


def get_current_ip():
    response = requests.get("https://ipv4.icanhazip.com")
    return response.text.strip()