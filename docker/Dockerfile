# Test-runner image for shop-bdd (Unit 4, Day 15). Runs the offline suites (unit, BDD on the
# in-memory stores, the events sandbox). It has no browser and no Android SDK: the live web suite
# needs a browser image, and mobile runs on a device (Device Farm), not in this container.
#
#   docker build -f docker/Dockerfile -t shop-bdd-tests:local .
#   docker run --rm --read-only --tmpfs /tmp --tmpfs /app/reports:uid=10001 shop-bdd-tests:local --suite offline --artifacts none

# Pinned by digest: the same bytes on every build (update deliberately, e.g. with Dependabot).
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes.
# The optional secret is for builds behind a TLS-inspecting proxy; it never enters the image.
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install -r requirements.txt

# Then the code. .dockerignore keeps out git data, CI files, reports, caches, and virtual environments.
COPY . .

ARG GIT_SHA=unknown
ENV GIT_SHA=${GIT_SHA}

# Non-root, fixed UID (matches "User": "10001" in the task definition).
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin runner \
    && mkdir -p /app/reports && chown runner /app/reports
USER 10001

ENTRYPOINT ["python", "-m", "framework.cloud.run_suite"]
CMD ["--suite", "offline"]
