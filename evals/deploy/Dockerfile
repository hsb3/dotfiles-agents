FROM alpine:3.20

ARG PB_VERSION=0.40.3
ARG TARGETARCH

RUN apk add --no-cache ca-certificates curl unzip
RUN set -e; case "$TARGETARCH" in \
      amd64) PB_SHA256=8d81b6b79add0e219373e922ebe1dddbee7f57fcff602e3585e0d2c654b983ce ;; \
      arm64) PB_SHA256=d5092815259f5bc2dffabf6a71da2168851c8d75c04d6e56f6e7a38c48941c70 ;; \
      *) echo "unsupported PocketBase architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL -o /tmp/pb.zip "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${TARGETARCH}.zip"; \
    echo "$PB_SHA256  /tmp/pb.zip" | sha256sum -c -; \
    unzip /tmp/pb.zip -d /pb; rm /tmp/pb.zip; /pb/pocketbase --version

WORKDIR /pb
COPY start.sh ./start.sh
COPY pb_public ./pb_public
COPY pb_hooks ./pb_hooks
RUN chmod +x /pb/start.sh

EXPOSE 8090
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -q -O- "http://127.0.0.1:${PORT:-8090}/api/health" >/dev/null 2>&1 || exit 1
CMD ["/pb/start.sh"]
