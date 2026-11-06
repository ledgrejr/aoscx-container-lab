FROM python:3.13.15-slim-bookworm@sha256:ad4c34ff79289506e235b40dce75d629e25f226b597a2455804220f037e07531

ARG APP_VERSION=0.1.0
ARG VCS_REF=unknown
ARG SOURCE_DATE_EPOCH=0

WORKDIR /app
COPY VERSION healthcheck.py ./
RUN test "${APP_VERSION}" = "$(cat VERSION)"

LABEL org.opencontainers.image.title="AOS-CX Container Lab health check" \
      org.opencontainers.image.description="Local process health heartbeat; no switch management access or listening ports" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/ledgrejr/aoscx-container-lab"

USER 65532:65532
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 CMD ["python", "/app/healthcheck.py", "--check"]
ENTRYPOINT ["python", "/app/healthcheck.py"]