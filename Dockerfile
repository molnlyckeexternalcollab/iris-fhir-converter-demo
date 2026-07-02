ARG IMAGE=containers.intersystems.com/intersystems/irishealth-community:latest-em

# ─── Stage 1: base — slow layers, cached as long as requirements don't change ───
FROM $IMAGE AS base

USER root

# APP_HOME controls both the build-time filesystem layout and the runtime path used by all scripts.
# It can be overridden at build time only: docker build --build-arg APP_HOME=/your/path .
# Changing it at runtime (docker-compose, k8s) without rebuilding will break the container.
ARG APP_HOME=/irisdev/app
ENV APP_HOME=${APP_HOME} \
	HOME="/home/${ISC_PACKAGE_MGRUSER}"

# See:
# For env vars: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GIEUNIX_unattended_parameters
# For image tags: https://containers.intersystems.com/contents/containers
# https://github.com/intersystems-community/iris-docker-zpm-usage-template/blob/master/module.xml
# TODO: https://github.com/grongierisc/iris-docker-multi-stage-script

# Packages installation and configuration
RUN set -eux; \
	# ---- Install packages ----
	apt-get update && \
	apt-get install -y --no-install-recommends \
	curl \
	git \
	nano \
	ncdu && \
	# ---- Clean up apt cache ----
	apt-get clean && \
	rm -rf /var/lib/apt/lists/*

# Create local folder for the application
RUN mkdir -p "${APP_HOME}" && \
	chown -R "${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP}" "${APP_HOME}"

USER ${ISC_PACKAGE_MGRUSER}

# Python stuff
# Note:
# 	PYTHONPATH — standard Python variable, tells the Python interpreter where to find modules
# 	PYTHON_PATH — a custom IRIS variable, not a Python standard. It points to the directory containing the Python executable
ENV IRISUSERNAME="SuperUser" \
	IRISPASSWORD="SYS" \
	IRISNAMESPACE="EAI" \
	PYTHONIOENCODING=UTF-8 \
	PYTHONUNBUFFERED=1 \
	PYTHON_PATH="${ISC_PACKAGE_INSTALLDIR}/bin/" \
	PYTHONPATH="${APP_HOME}/src/CDS/python:${APP_HOME}/src/EAI/python:${APP_HOME}/src/DSE/python" \
	LD_LIBRARY_PATH="${ISC_PACKAGE_INSTALLDIR}/bin:${LD_LIBRARY_PATH}" \
	PATH="${HOME}/.local/bin:${ISC_PACKAGE_INSTALLDIR}/bin:${PATH}"

# Copy only requirements first — pip install is cached until any requirements file changes
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} requirements*.txt "${APP_HOME}/"

# Install the requirements, force write into the system site-packages directory
RUN pip3 install -r "${APP_HOME}/requirements.txt" \
	--no-cache-dir \
	--break-system-packages

# ─── Stage 2: app — fast rebuild, only re-runs when source code changes ──────
FROM base AS app

USER root

COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} ./key/iris.*.key /tmp/
RUN cp "/tmp/iris.$(uname -m).key" "${ISC_PACKAGE_INSTALLDIR}/mgr/iris.key"

USER ${ISC_PACKAGE_MGRUSER}

# Copy the full source code
COPY --chown=${ISC_PACKAGE_MGRUSER}:${ISC_PACKAGE_IRISGROUP} . "${APP_HOME}/"

# Cleanup
RUN rm -f "${ISC_PACKAGE_INSTALLDIR}/mgr/alerts.log"; \
    rm -f "${ISC_PACKAGE_INSTALLDIR}/mgr/IRIS.WIJ"; \
    rm -f "${ISC_PACKAGE_INSTALLDIR}/mgr/journal/*"; \
    rm -f "${ISC_PACKAGE_INSTALLDIR}/mgr/iristemp/IRIS.DAT"; \
    rm -fR /tmp/*

# Expose ports
# 52773  — IRIS web gateway (HTTP) intentionally not in EXPOSE list because we use the webgateway
# 1972   — IRIS superserver (native protocol)
# 62115  — HL7 TCP inbound connector
EXPOSE 1972 62115

# Note: we need the entry point to be: /tini -- /irisdev/app/docker-entrypoint.sh
# but we can't write ENTRYPOINT [ "/tini", "--", "${APP_HOME}/docker-entrypoint.sh" ]
# because the JSON (exec) form bypasses the shell, so ${APP_HOME} is passed literally to tini.
# The workaround is to invoke sh explicitly so the variable is expanded at runtime,
# while still forwarding CMD args ("$@") to docker-entrypoint.sh.
ENTRYPOINT ["/bin/sh", "-c", "exec /tini -- \"${APP_HOME}/docker-entrypoint.sh\" \"$@\"", "--"]

CMD [ "iris" ]