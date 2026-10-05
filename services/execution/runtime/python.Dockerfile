# Supply reviewed digest-pinned upstream images; there is no mutable default.
ARG PYTHON_BASE
FROM ${PYTHON_BASE}
COPY services/execution/runtime/launch.py /opt/socrat/launch.py
RUN mkdir /work && chown 10001:10001 /work
USER 10001:10001
WORKDIR /work
