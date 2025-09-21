import os
import time
import csv
import subprocess
from io import StringIO

from .base import BaseChecker

class IPerfChecker(BaseChecker):
    """iperf network performance test"""

    def enabled(self) -> bool:
        return self.get_boolean_from_string(os.environ.get('IPERF_ENABLED', 'false'))

    def check(self) -> int:
        interval_secs = self.get_timeout('IPERF_INTERVAL', '1h')
        max_timeout_secs = self.get_timeout('IPERF_TIMEOUT', '30s')
        duration_secs = self.get_timeout('IPERF_DURATION', '10s')
        jobs = os.environ.get('IPERF_JOBS', '1')

        targets = self.get_targets('IPERF_TARGETS')

        for server in targets:
            start_time = time.time()
            data, success = self.run_test('upload', server, max_timeout_secs, duration_secs, jobs)
            if success:
                self.send_upload_metrics(data, start_time, server)
            else:
                break

            start_time = time.time()
            data, success = self.run_test('download', server, max_timeout_secs, duration_secs, jobs)
            if success:
                self.send_download_metrics(data, start_time, server)
            else:
                break
 
        print("All tests completed successfully")
        return interval_secs

    def run_test(self, direction: str, server: str, max_timeout_secs: int, duration_secs: int, jobs: str) -> tuple:
        """Run iperf test with specified direction and return data and success status"""
        try:
            print(f"Running {direction} test to server {server} using {jobs} connection(s)...")

            cmd = f"iperf -c {server} -t {duration_secs} -P {jobs} -y C"
            if direction == 'download':
                cmd += " -R"

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=True,
                timeout=max_timeout_secs
            )

            csv_output = result.stdout.decode('utf-8').strip()
            data = self.parse_csv_output(csv_output)
            return data, True

        except subprocess.TimeoutExpired:
            print(f"** iperf {direction} timeout after {max_timeout_secs} seconds")
            return None, False

        except subprocess.CalledProcessError as e:
            stdout = e.stdout.decode().rstrip() if e.stdout else ""
            stderr = e.stderr.decode().rstrip() if e.stderr else ""

            print(f"** iperf {direction} failed (rc: {e.returncode})")
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")

            return None, False

        except Exception as e:
            print(f"** iperf {direction} unexpected error: {e}")
            return None, False

    def parse_csv_output(self, csv_output: str) -> list:
        """Parse iperf CSV output into structured data"""
        data = []
        reader = csv.reader(StringIO(csv_output))

        for row in reader:
            if len(row) >= 9:
                record = {
                    'timestamp': row[0],
                    'client_ip': row[1],
                    'client_port': row[2],
                    'server_ip': row[3],
                    'server_port': row[4],
                    'thread_id': row[5],
                    'interval': row[6],
                    'bytes': int(row[7]),
                    'bandwidth': int(row[8])
                }
                data.append(record)
            return data

    def send_upload_metrics(self, data: list, start_time: float, server: str) -> None:
        """Send upload metrics to InfluxDB"""
        duration_ms = (time.time() - start_time) * 1000  # ms

        try:
            if not data:
                print("No data received for upload metrics")
                return

            summary = data[-1]
            bandwidth_mbps = summary['bandwidth'] / 1_000_000
            thread_count = 1 if summary['thread_id'] != '-1' else len(data) - 1

            print(f"UPLOAD ** {bandwidth_mbps:.2f} Mbps, threads: {thread_count}, duration: {duration_ms:.0f} ms")

            # Send upload metrics
            self.client.metric(
                self.bucket,
                tags={
                    'type': 'iperf',
                    'direction': 'upload',
                    'result': 'success',
                    'server': server,
                },
                values={
                    'bandwidth': round(bandwidth_mbps, 2),
                    'threads': thread_count,
                    'bytes': summary['bytes'],
                    'duration': int(duration_ms),
                }
            )

        except Exception as e:
            print(f"Failed to send iperf upload metrics: {e}")
            print(f"Data received: {data}")

    def send_download_metrics(self, data: list, start_time: float, server: str) -> None:
        """Send download metrics to InfluxDB"""
        duration_ms = (time.time() - start_time) * 1000  # ms

        try:
            if not data:
                print("No data received for download metrics")
                return

            summary = data[-1]
            bandwidth_mbps = summary['bandwidth'] / 1_000_000
            thread_count = 1 if summary['thread_id'] != '-1' else len(data) - 1

            print(f"DOWNLOAD ** {bandwidth_mbps:.2f} Mbps, threads: {thread_count}, duration: {duration_ms:.0f} ms")

            # Send download metrics
            self.client.metric(
                self.bucket,
                tags={
                    'type': 'iperf',
                    'direction': 'download',
                    'result': 'success',
                    'server': server,
                },
                values={
                    'bandwidth': round(bandwidth_mbps, 2),
                    'threads': thread_count,
                    'bytes': summary['bytes'],
                    'duration': int(duration_ms),
                }
            )

        except Exception as e:
            print(f"Failed to send iperf download metrics: {e}")
            print(f"Data received: {data}")
