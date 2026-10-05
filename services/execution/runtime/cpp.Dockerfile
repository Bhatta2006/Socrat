ARG PYTHON_BASE
FROM ${PYTHON_BASE} AS python
ARG CPP_BASE
FROM ${CPP_BASE}
COPY --from=python /usr/local /usr/local
COPY services/execution/runtime/launch.py /opt/socrat/launch.py
RUN mkdir /work && chown 10001:10001 /work
USER 10001:10001
WORKDIR /work
