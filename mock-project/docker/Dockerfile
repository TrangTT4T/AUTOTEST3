# syntax=docker/dockerfile:1
# Test-runner image for the Swag Labs mock project (Unit 5).
#
# Base: Microsoft's official Playwright image - Chromium, Firefox and WebKit with every system
# library they need, at the browser builds that playwright==1.63.0 expects. Pinned by DIGEST, so
# every build starts from the same bytes; update deliberately (e.g. with Dependabot), never by
# accident through a moved tag.
#
#   docker build -f docker/Dockerfile -t swaglabs-tests:local .
#   docker run --rm --init --ipc=host --read-only --tmpfs /tmp \
#       -v "$PWD/reports:/work/reports" swaglabs-tests:local -n 4 --persona problem_user
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble@sha256:72bd171a9ffc2b4b59532aaa6210e21014d07093120dc25528870c0b840da1f0

LABEL org.opencontainers.image.title="swaglabs-tests" \
      org.opencontainers.image.description="BDD + Playwright suite for Swag Labs (ATEST03 Unit 5)"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Chromium and Firefox write profiles under $HOME: point it at the tmpfs of a read-only container.
    HOME=/tmp

WORKDIR /work

# Dependencies first: this layer is rebuilt only when requirements.txt changes.
# The optional secret is for builds behind a TLS-inspecting proxy; it never enters an image layer.
COPY requirements.txt .
RUN --mount=type=secret,id=proxy_ca,required=false \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install -r requirements.txt \
    && python -m playwright --version

# Then the code (.dockerignore keeps out reports, caches, docs and virtual environments).
COPY . .

# Non-root: the image's own pwuser (uid 1001 - the same uid as GitHub's hosted runner user, so
# files written into a mounted reports/ folder belong to the runner).
RUN mkdir -p /work/reports && chown pwuser:pwuser /work/reports
USER pwuser

# No cache provider: the code directory is read-only at run time. Arguments after the image name
# are pytest arguments; the default runs the whole suite on four workers.
ENTRYPOINT ["python", "-m", "pytest", "-p", "no:cacheprovider"]
CMD ["-n", "4"]
