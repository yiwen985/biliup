# Deploy Biliup
FROM python:3.9-slim as biliup
ENV TZ=Asia/Shanghai
VOLUME /opt

COPY . /biliup
RUN \
  set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends ffmpeg g++; \
  cd /biliup && \
  pip3 install --no-cache-dir quickjs && \
  pip3 install -e . && \
  # Clean up \
  apt-get --purge remove -y g++ && \
  apt-get autoremove -y && \
  apt-get clean -y && \
  rm -rf \
  /var/cache/debconf/* \
  /var/lib/apt/lists/* \
  /var/log/* \
  /var/tmp/* \
  && rm -rf /tmp/*

WORKDIR /opt

ENTRYPOINT ["biliup"]
