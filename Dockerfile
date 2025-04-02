FROM python:3.12

ARG TARGETPLATFORM
ARG TARGETARCH
ARG TARGETVARIANT
RUN printf "I'm building for TARGETPLATFORM=${TARGETPLATFORM}" \
    && printf ", TARGETARCH=${TARGETARCH}" \
    && printf ", TARGETVARIANT=${TARGETVARIANT} \n" \
    && printf "With uname -s : " && uname -s \
    && printf "and  uname -m : " && uname -m

# Update OS and install packages
RUN apt-get update --yes && \
    apt-get dist-upgrade --yes && \
    apt-get install --yes \
      screen \
      unzip \
      vim \
      zip

# Create an application user
RUN useradd app_user --create-home

ARG APP_DIR="/opt/flight_sql_proxy"
RUN mkdir --parents ${APP_DIR} && \
    chown app_user:app_user ${APP_DIR}

USER app_user

WORKDIR ${APP_DIR}

# Setup a Python Virtual environment
ENV VIRTUAL_ENV=${APP_DIR}/.venv
RUN python3 -m venv ${VIRTUAL_ENV} && \
    echo ". ${VIRTUAL_ENV}/bin/activate" >> ~/.bashrc

# Set the PATH so that the Python Virtual environment is referenced for subsequent RUN steps (hat tip: https://pythonspeed.com/articles/activate-virtualenv-dockerfile/)
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# Upgrade pip, setuptools, and wheel
RUN pip install --upgrade setuptools pip wheel

# Install the Python package (from source)
RUN pwd
COPY --chown=app_user:app_user pyproject.toml README.md LICENSE .
COPY --chown=app_user:app_user src ./src

RUN pip install .

# Cleanup source code
RUN rm -rf pyproject.toml README.md ./src

# Open web-socket port
EXPOSE 8765

ENTRYPOINT ["flight-sql-websocket-proxy-server"]
