ARG VERSION=latest

# Stage: install application
# -------------------------------------
FROM python:3.13.5-slim AS builder

WORKDIR /build

RUN \
  set -e; \
  # Install prerequisites and certificates
  export DEBIAN_FRONTEND=noninteractive; \
  apt-get update; \
  apt-get install -y \
    curl \
    gnupg \
    ca-certificates \
    iputils-ping \
    iperf \
    iperf3 \
    ; \
  update-ca-certificates

RUN \
  set -e; \
  # Install speedtest tool
  curl -s https://packagecloud.io/install/repositories/ookla/speedtest-cli/script.deb.sh -o configure.sh; \
  ls -al; \
  chmod +x configure.sh; \
  ./configure.sh; \
  apt-get install speedtest;

COPY ./code .

# Install Python dependencies
RUN pip install --no-cache-dir -r ./requirements.txt

# Install network-monitor application
RUN pip install --no-cache-dir .

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN \
  set -e; \
  # Cleanup
  apt-get autoremove -y; \
  apt-get clean; \
  rm -rf /build /tmp/* /var/lib/apt/lists/*;


# Stage: prepare image
# -------------------------------------
FROM scratch

ARG VERSION

LABEL version=${VERSION}
LABEL description="Network monitor tool and reporter (influxdb2)"
LABEL maintainer="Dmitry Korobkov [https://github.com/DK6v/docker-network-monitor]"

COPY --from=builder / /

CMD [ "python", "-u", "-m", "network_monitor" ]
ENTRYPOINT ["/entrypoint.sh" ]
