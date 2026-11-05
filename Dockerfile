FROM python:3.13-alpine3.22@sha256:e81548ac35b07a3bd4805f275107592ef458b1e893c0e04d45aedaa19416cca5 AS build
WORKDIR /build
COPY pyproject.toml ./
COPY cleanup_scanner ./cleanup_scanner
RUN python -m pip install --no-cache-dir --no-deps --prefix=/install . \
    && mkdir -p /runtime/usr \
    && cp -a /usr/local /runtime/usr/local \
    && rm -rf /runtime/usr/local/include /runtime/usr/local/share/man \
        /runtime/usr/local/lib/pkgconfig /runtime/usr/local/lib/python3.13/config-* \
        /runtime/usr/local/lib/python3.13/ensurepip \
        /runtime/usr/local/lib/python3.13/idlelib /runtime/usr/local/lib/python3.13/turtledemo \
        /runtime/usr/local/lib/python3.13/test \
    && rm -rf /runtime/usr/local/lib/python3.13/site-packages \
    && mkdir /runtime/usr/local/lib/python3.13/site-packages \
    && cp -a /install/lib/python3.13/site-packages/. /runtime/usr/local/lib/python3.13/site-packages/ \
    && find /runtime -type d -name __pycache__ -exec rm -rf '{}' + \
    && find /runtime/usr/local/bin -name 'pip*' -delete \
    && find /runtime -type f -name '*.a' -delete

FROM alpine:3.22@sha256:2e0b81d60597f449baa56dc25d355367869d2dca4cd57e866f1e2b52af3eb55f
RUN apk add --no-cache libbz2 libexpat libffi libgcc ncurses-libs readline sqlite-libs xz-libs zlib libssl3 libcrypto3 \
    && addgroup -g 10001 scanner \
    && adduser -D -H -u 10001 -G scanner -s /sbin/nologin scanner
COPY --from=build /runtime/ /
ARG SOURCE_URL=https://github.com/matthiasbalke/disk-space-cleanup-helper
ARG REVISION=unknown
LABEL org.opencontainers.image.source=$SOURCE_URL \
      org.opencontainers.image.revision=$REVISION
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
USER 10001:10001
ENTRYPOINT ["python", "-m", "cleanup_scanner"]
CMD ["--help"]
