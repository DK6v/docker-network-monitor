import os
import time
import requests

from .base import BaseChecker

class HttpChecker(BaseChecker):
    """Checker for HTTP-request monitoring"""

    def enabled(self) -> bool:
        return self.get_boolean_from_string(os.environ.get('HTTP_ENABLED', 'false'))

    def check(self) -> int:
        max_timeout_secs = self.get_timeout('HTTP_TIMEOUT', '5s')
        expected_status = list(map(int, filter(None,
            [url.strip() for url in os.environ.get('HTTP_EXPECTED_STATUS', '200;301;').split(';')])))
        targets = self.get_targets('HTTP_TARGETS')

        for target in targets:
            status_code = None
            start_time = time.time()

            url = "http://" + target
            try:
                response = requests.get(url, timeout=max_timeout_secs, verify=True)
                duration_ms = (time.time() - start_time) * 1000
                status_code = response.status_code

                if status_code in expected_status:
                    print('{:30} ** success ({}) {:.1f} ms'.format('GET ' + url, status_code, duration_ms))
                else:
                    print('{:30} ** failed ({}) {:.1f} ms'.format('GET ' + url, status_code, duration_ms))

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                print('{:30} ** {}'.format('GET ' + url, e))

            self.client.metric(
                self.bucket,
                tags={
                    'type': 'http',
                    'method': 'GET',
                    'url': url,
                    'result': 'success' if (status_code in expected_status) else 'failed'
                },
                values={
                    'duration': int(duration_ms),
                }
            )

        return self.get_timeout('HTTP_INTERVAL', '60s')
