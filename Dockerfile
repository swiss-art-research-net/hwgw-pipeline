FROM python:3.8

RUN apt-get update && apt-get -y upgrade && \
    apt-get install -y \
        sudo \
        curl \
        wget \
        locales \
        parallel \
        time \
        python3-distutils \
        openjdk-17-jdk && \
    locale-gen en_US.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8 \
    LANGUAGE=en_US:en \
    LC_ALL=en_US.UTF-8

# Set the timezone
RUN ln -sf /usr/share/zoneinfo/Europe/Zurich /etc/localtime

RUN pip install --no-cache-dir \
    python-decouple \
    requests-toolbelt \
    date-parser-sari \
    lxml \
    urllib3 \
    requests \
    edtf \
    tqdm \
    rdflib \
    sari-field-definitions-generator \
    sparqlwrapper \
    PyYAML \
    Pillow \
    pytz \
    pyshacl \
    python-dateutil \
    semantic-field-definition-generator==1.4.1 \
    tqdm \
    rdflib \
    deepl \
    pytest


RUN mkdir -p /libs /java/bin /scripts /data /mapping /logs
RUN wget https://github.com/isl/x3ml/releases/download/2.2.0/x3ml-engine-2.2.0-exejar.jar -O /libs/x3ml-engine-exejar.jar

# Install task runner (http://taskfile.dev)
RUN sh -c "$(curl -sSL https://taskfile.dev/install.sh)" -- -d

# Copy x3ml service
COPY services/jobs/x3ml/java/bin/ /java/bin/
# Copy scripts
COPY scripts/ /scripts/

# no mappings yet
# COPY mapping/ /mapping/

# VOLUME /data
# VOLUME /mapping
# VOLUME /logs
WORKDIR /scripts

ENTRYPOINT sh -c 'java -cp /libs/x3ml-engine-exejar.jar:/java/bin X3MLEngineService > /logs/mapping-log.log 2>&1'
