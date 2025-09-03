import os
import ping3
from .base import BaseChecker

class PingChecker(BaseChecker):
    """Checker for ping monitoring"""

    def enabled(self) -> bool:
        return self.get_boolean_from_string(os.environ.get('PING_ENABLED', 'false'))

    def check(self) -> int:
        max_timeout_secs = self.get_timeout('PING_TIMEOUT', '5s')
        hosts = self.get_targets('PING_TARGETS')

        for host in hosts:
            try:
                duration_ms = ping3.ping(host, unit='ms', timeout=max_timeout_secs)

                if duration_ms is not None:
                    print('{:30} ** success'.format('ping ' + host))
                    self.client.metric(
                        self.bucket,
                        tags={
                            'type': 'ping',
                            'host': host,
                            'result': 'success',
                        },
                        values={
                            'duration': int(duration_ms),
                        },
                    )
                else:
                    print('{:30} ** timeout'.format('ping ' + host))
                    self.client.metric(
                        self.bucket,
                        tags={
                            'type': 'ping',
                            'host': host,
                            'result': 'timeout',
                        },
                        values={
                            'duration': int(-1),
                        },
                    )

            except Exception as e:
                print('{:30} ** {}'.format('ping ' + host, e))
                self.client.metric(
                    self.bucket,
                    tags={
                        'type': 'ping',
                        'host': host,
                        'result': 'failed',
                    },
                    values={
                        'duration': int(-1),
                    },
                )

        return self.get_timeout('PING_INTERVAL', '60s')
