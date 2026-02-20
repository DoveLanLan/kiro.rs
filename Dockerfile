# syntax=docker/dockerfile:1.7
### NOTE:
### - This Dockerfile uses BuildKit features (cache mounts). Make sure BuildKit is enabled.
### - Docker Compose v2 usually enables BuildKit by default.

FROM node:22-alpine AS frontend-builder

WORKDIR /app/admin-ui
COPY admin-ui/package.json ./
RUN npm install -g pnpm
COPY admin-ui ./
RUN --mount=type=cache,target=/root/.local/share/pnpm/store,sharing=locked \
    pnpm install && pnpm build

FROM rust:1.92-alpine AS builder

RUN apk add --no-cache musl-dev openssl-dev openssl-libs-static

WORKDIR /app
ARG CARGO_REGISTRY_MIRROR=""
ARG CARGO_HTTP_MULTIPLEXING="true"
ARG CARGO_HTTP_TIMEOUT="600"
ENV CARGO_HTTP_MULTIPLEXING=${CARGO_HTTP_MULTIPLEXING}
ENV CARGO_HTTP_TIMEOUT=${CARGO_HTTP_TIMEOUT}
ENV CARGO_NET_GIT_FETCH_WITH_CLI=true

COPY Cargo.toml Cargo.lock* ./
COPY src ./src
COPY --from=frontend-builder /app/admin-ui/dist /app/admin-ui/dist

RUN if [ -n "${CARGO_REGISTRY_MIRROR}" ]; then \
      mkdir -p /root/.cargo && \
      printf '%s\n' \
        '[registries.crates-io]' \
        "index = \"${CARGO_REGISTRY_MIRROR}\"" \
        > /root/.cargo/config.toml ; \
    fi

RUN --mount=type=cache,target=/usr/local/cargo/registry,sharing=locked \
    --mount=type=cache,target=/usr/local/cargo/git,sharing=locked \
    --mount=type=cache,target=/app/target,sharing=locked \
    if [ -f Cargo.lock ]; then cargo build --release --locked; else cargo build --release; fi && \
    install -m 0755 /app/target/release/kiro-rs /app/kiro-rs

FROM alpine:3.21

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apk/repositories && \
    apk add --no-cache ca-certificates

WORKDIR /app
COPY --from=builder /app/kiro-rs /app/kiro-rs

VOLUME ["/app/config"]

EXPOSE 8990

CMD ["./kiro-rs", "-c", "/app/config/config.json", "--credentials", "/app/config/credentials.json"]
