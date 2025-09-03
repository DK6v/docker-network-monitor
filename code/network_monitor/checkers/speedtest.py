import os
import time
import json
import subprocess

from .base import BaseChecker

class SpeedtestChecker(BaseChecker):
    """Speedtest by Ookla"""

    def enabled(self) -> bool:
        return self.get_boolean_from_string(os.environ.get('SPEEDTEST_ENABLED', 'false'))

    def check(self) -> int:
        max_timeout_secs = self.get_timeout('SPEEDTEST_TIMEOUT', '300s')

        start_time = time.time()

        try:
            print("Start Speedtest by Ookla (timeout {}s)".format(max_timeout_secs))
            result = subprocess.run(
                "speedtest --accept-license --accept-gdpr --format=json",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=True,
                timeout=max_timeout_secs
            )

            data = json.loads(result.stdout.decode('utf-8'))
            self.send_metrics(data, start_time)

        except subprocess.TimeoutExpired:
            print("** speedtest timeout after {} seconds".format(max_timeout_secs))
            self.send_timeout_metrics(start_time)

        except subprocess.CalledProcessError as e:
            stdout = e.stdout.decode().rstrip() if e.stdout else ""
            stderr = e.stderr.decode().rstrip() if e.stderr else ""

            print(f"** speedtest failed (rc: {e.returncode})")
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")

            self.send_error_metrics(start_time, e.returncode)

        except json.JSONDecodeError as e:
            print(f"** speedtest JSON decode error: {e}")
            self.send_error_metrics(start_time, "json_error")

        except Exception as e:
            print(f"** speedtest unexpected error: {e}")
            self.send_error_metrics(start_time, "unexpected_error")

        return self.get_timeout('SPEEDTEST_INTERVAL', '1h')  # ← Исправить название переменной

    def send_metrics(self, data: dict, start_time: float) -> None:
        """Send speedtest metrics to InfluxDB"""
        duration_ms = (time.time() - start_time) * 1000  # ms

        try:
            download = data.get('download', {}).get('bandwidth')
            upload = data.get('upload', {}).get('bandwidth')
            ping_latency = data.get('ping', {}).get('latency')
            ping_jitter = data.get('ping', {}).get('jitter')
            ping_high = data.get('ping', {}).get('high')
            ping_low = data.get('ping', {}).get('low')
            packet_loss = data.get('packetLoss')
            server = data.get('server', {}).get('name', 'unknown')

            # Convert bits/s to Mbps
            download_mbps = (float(download) * 8 / 1_000_000) if download else 0.0
            upload_mbps = (float(upload) * 8 / 1_000_000) if upload else 0.0

            print('{:30} ** success {:.1f} ms'.format('Speedtest by Ookla', duration_ms))
            print(json.dumps(data, indent=2))

            self.client.metric(
                self.bucket,
                tags={
                    'type': 'speedtest',
                    'server': server,
                    'result': 'success'
                },
                values={
                    'duration': int(duration_ms),
                    'download': round(download_mbps, 2),
                    'upload': round(upload_mbps, 2),
                    'ping_latency': round(ping_latency, 2) if ping_latency else 0,
                    'ping_jitter': round(ping_jitter, 2) if ping_jitter else 0,
                    'ping_high': round(ping_high, 2) if ping_high else 0,
                    'ping_low': round(ping_low, 2) if ping_low else 0,
                    'packet_loss': round(packet_loss, 2) if packet_loss else 0
                }
            )

        except Exception as e:
            print(f"Failed to send speedtest metrics: {e}")

    def send_timeout_metrics(self, start_time: float) -> None:
        """Send timeout metrics"""
        duration_ms = (time.time() - start_time) * 1000

        self.client.metric(
            self.bucket,
            tags={
                'type': 'speedtest',
                'result': 'timeout'
            },
            values={
                'duration': int(duration_ms)
            }
        )

    def send_error_metrics(self, start_time: float, error_type: str) -> None:
        """Send error metrics"""
        duration_ms = (time.time() - start_time) * 1000

        self.client.metric(
            self.bucket,
            tags={
                'type': 'speedtest',
                'result': 'error',
                'error_type': str(error_type)
            },
            values={
                'duration': int(duration_ms)
            }
        )
