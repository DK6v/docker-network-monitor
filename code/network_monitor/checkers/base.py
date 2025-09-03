import os
from abc import ABC, abstractmethod
from typing import Dict, Any

from ..client import TelegrafClient

class BaseChecker(ABC):
    """Abstract base class for all checkers"""

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self.bucket = os.environ.get('INFLUXDB_METRIC', 'network-monitor')

        # Create Telegraf client
        host = str(os.environ.get('INFLUXDB_HOST', 'localhost'))
        port = int(os.environ.get('INFLUXDB_PORT', '8086'))
        self.client = TelegrafClient(host, port)
        print(f'Created client: {self.name}, {host}:{port} -> {self.bucket}'),

    @abstractmethod
    def enabled(self) -> bool:
        """Returns true if checker enabled, false otherwise"""
        pass

    @abstractmethod
    def check(self) -> int:
        """Execute check and return interval until next run"""
        pass

    def get_timeout(self, env_var: str, default: str) -> int:
        """Get timeout from environment variable"""
        return self.get_seconds_from_string(os.environ.get(env_var, default))

    def get_targets(self, env_var: str) -> list:
        """Get targets list from environment variable"""
        return list(filter(None, [h.strip() for h in os.environ.get(env_var, '').split(';')]))

    def get_seconds_from_string(self, value: str) -> int:
        """Convert time to seconds"""
        if value.endswith('s'):
            return int(value[:-1])
        elif value.endswith('m'):
            return int(value[:-1]) * 60
        elif value.endswith('h'):
            return int(value[:-1]) * 3600
        else:
            return int(value)

    def get_boolean_from_string(self, value: str) -> bool:
        """Convert string to boolean"""
        if isinstance(value, bool):
            return value
        return value.lower() in ('true', '1', 't', 'y', 'yes', 'on', 'enable', 'enabled')