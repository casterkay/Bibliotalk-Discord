FROM alpine:3.20

ARG PB_VERSION=0.36.5
ARG TARGETARCH

RUN apk add --no-cache ca-certificates curl unzip

WORKDIR /pb
# Unset proxy env so curl isn't broken by Docker Desktop's placeholder http://proxy-host:port
RUN PB_ARCH="amd64" \
  && if [ "${TARGETARCH}" = "arm64" ]; then PB_ARCH="arm64"; fi \
  && unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy NO_PROXY no_proxy \
  && curl -fsSL -o pocketbase.zip "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${PB_ARCH}.zip" \
  && unzip pocketbase.zip \
  && rm pocketbase.zip \
  && chmod +x /pb/pocketbase

EXPOSE 8090

CMD ["/pb/pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb/pb_data", "--migrationsDir=/pb/pb_migrations"]
