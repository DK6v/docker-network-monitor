import os
import time
import json
import subprocess

from .base import BaseChecker

class IPerf3Checker(BaseChecker):
    """iperf3 network performance test"""

    def enabled(self) -> bool:
        return self.get_boolean_from_string(os.environ.get('IPERF3_ENABLED', 'false'))

    def check(self) -> int:
        interval_secs = self.get_timeout('IPERF3_INTERVAL', '1h')
        max_timeout_secs = self.get_timeout('IPERF3_TIMEOUT', '30s')
        duration_secs = self.get_timeout('IPERF3_DURATION', '10s')
        jobs = os.environ.get('IPERF3_JOBS', '1')
        server = os.environ.get('IPERF3_SERVER')

        if not server:
            print("** iperf3 server not specified (IPERF3_SERVER environment variable)")
            self.send_error_metrics(time.time(), "server_not_specified")
            return self.get_timeout('IPERF3_INTERVAL', '1h')

        start_time = time.time()
        data, success = self.run_test('upload', server, max_timeout_secs, duration_secs, jobs)
        if success:
            self.send_upload_metrics(data, start_time, server)
        else:
            return interval_secs

        start_time = time.time()
        data, success = self.run_test('download', server, max_timeout_secs, duration_secs, jobs)
        if success:
            self.send_download_metrics(data, start_time, server)
        else:
            return interval_secs

        print("All tests completed successfully")
        return interval_secs

    def run_test(self, direction: str, server: str, max_timeout_secs: int, duration_secs: int, jobs: str) -> tuple:
        """Run iperf3 test with specified direction and return data and success status"""
        try:
            print(f"Running {direction} test to server {server} using {jobs} parallel connection(s)...")

            if direction == 'upload':
                cmd = f"iperf3 -c {server} -J --time {duration_secs} -P {jobs}"
            else:
                cmd = f"iperf3 -c {server} -J --time {duration_secs} -P {jobs} -R"

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                check=True,
                timeout=max_timeout_secs
            )
            
            data = json.loads(result.stdout.decode('utf-8'))
            return data, True

        except subprocess.TimeoutExpired:
            print(f"** iperf3 {direction} timeout after {max_timeout_secs} seconds")
            return None, False

        except subprocess.CalledProcessError as e:
            stdout = e.stdout.decode().rstrip() if e.stdout else ""
            stderr = e.stderr.decode().rstrip() if e.stderr else ""

            print(f"** iperf3 {direction} failed (rc: {e.returncode})")
            if stdout:
                print(f"STDOUT: {stdout}")
            if stderr:
                print(f"STDERR: {stderr}")

            return None, False

        except json.JSONDecodeError as e:
            print(f"** iperf3 {direction} JSON decode error: {e}")
            return None, False

        except Exception as e:
            print(f"** iperf3 {direction} unexpected error: {e}")
            return None, False

    def send_upload_metrics(self, data: dict, start_time: float, server: str) -> None:
        """Send upload metrics to InfluxDB"""
        duration_ms = (time.time() - start_time) * 1000  # ms

        try:
            # Get connection info
            connected_list = data.get('start', {}).get('connected', [])
            if connected_list:
                remote_host = connected_list[0].get('remote_host', server)
            else:
                remote_host = server

            # Parse upload test results
            end_data = data.get('end', {})
            result_data = end_data.get('sum_sent', {})
            bandwidth_bps = result_data.get('bits_per_second', 0)
            retransmits = result_data.get('retransmits', 0)

            # Convert to Mbps
            bandwidth_mbps = bandwidth_bps / 1_000_000

            print(f"UPLOAD ** {bandwidth_mbps:.2f} Mbps, retransmits: {retransmits}, duration: {duration_ms:.0f} ms")

            # Send upload metrics
            self.client.metric(
                self.bucket,
                tags={
                    'type': 'iperf3',
                    'direction': 'upload',
                    'result': 'success',
                    'server': server,
                },
                values={
                    'server': remote_host,
                    'bandwidth': round(bandwidth_mbps, 2),
                    'retransmits': retransmits,
                    'duration': int(duration_ms),
                }
            )

        except Exception as e:
            print(f"Failed to send iperf3 upload metrics: {e}")
            print(f"Data received: {json.dumps(data, indent=2) if 'data' in locals() else 'No data available'}")

    def send_download_metrics(self, data: dict, start_time: float, server: str) -> None:
        """Send download metrics to InfluxDB"""
        duration_ms = (time.time() - start_time) * 1000  # ms

        try:
            # Get connection info
            connected_list = data.get('start', {}).get('connected', [])
            if connected_list:
                remote_host = connected_list[0].get('remote_host', server)
            else:
                remote_host = server

            # Parse download test results
            end_data = data.get('end', {})
            result_data = end_data.get('sum_received', {})
            bandwidth_bps = result_data.get('bits_per_second', 0)
            # For download, retransmits might be in sum_sent
            retransmits = end_data.get('sum_sent', {}).get('retransmits', 0)

            # Convert to Mbps
            bandwidth_mbps = bandwidth_bps / 1_000_000

            print(f"DOWNLOAD ** {bandwidth_mbps:.2f} Mbps, retransmits: {retransmits}, duration: {duration_ms:.0f} ms")

            # Send download metrics
            self.client.metric(
                self.bucket,
                tags={
                    'type': 'iperf3',
                    'direction': 'download',
                    'result': 'success',
                    'server': server,
                },
                values={
                    'server': remote_host,
                    'bandwidth': round(bandwidth_mbps, 2),
                    'retransmits': retransmits,
                    'duration': int(duration_ms),
                }
            )

        except Exception as e:
            print(f"Failed to send iperf3 download metrics: {e}")
            print(f"Data received: {json.dumps(data, indent=2) if 'data' in locals() else 'No data available'}")

    def send_timeout_metrics(self, start_time: float, direction: str) -> None:
        """Send timeout metrics for specific direction"""
        duration_ms = (time.time() - start_time) * 1000

        self.client.metric(
            self.bucket,
            tags={
                'type': 'iperf3',
                'direction': direction,
                'result': 'timeout',
            },
            values={
                'duration': int(duration_ms),
            }
        )

    def send_error_metrics(self, start_time: float, error_type: str, direction: str) -> None:
        """Send error metrics for specific direction"""
        duration_ms = (time.time() - start_time) * 1000

        self.client.metric(
            self.bucket,
            tags={
                'type': 'iperf3',
                'direction': direction,
                'result': 'error',
            },
            values={
                'error_type': str(error_type),
                'duration': int(duration_ms),
            }
        )
