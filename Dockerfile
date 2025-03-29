FROM alpine:3.21 AS builder
ARG KOSIT_VALIDATOR_VERSION=1.5.0

# download kosit validator & symlink validationtool-standalone to our version
RUN wget -O /tmp/validator.zip https://github.com/itplr-kosit/validator/releases/download/v${KOSIT_VALIDATOR_VERSION}/validator-${KOSIT_VALIDATOR_VERSION}-distribution.zip && \
    unzip /tmp/validator.zip -d /kosit-validator && \
    cd /kosit-validator && \
    ln -sf validationtool-${KOSIT_VALIDATOR_VERSION}-standalone.jar validationtool-standalone.jar

# FROM --platform=linux/amd64 eclipse-temurin:21 TODO: causes errors, when used without platform flag
FROM openjdk:17-jdk-slim

RUN apt-get update -qq && \
    apt-get install -y --force-yes curl && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

# Set working directory inside the container
WORKDIR /java-app

# Copy the validation tool and merged configuration
COPY --from=builder /kosit-validator /java-app
COPY configuration /java-app/configuration

HEALTHCHECK --interval=30s --timeout=10s --start-period=3s --retries=10 \
  CMD curl -fsS http://127.0.0.1:80/server/health | grep -q "<ns2:status>UP</ns2:status>"

CMD ["java", "-jar", "validationtool-standalone.jar",\
"-s", "configuration/factur-x/1.07.2/scenarios.xml", "-r", "configuration/factur-x/1.07.2",\
"-s", "configuration/xrechnung/2.3.1_2023-05-12/scenarios.xml", "-r", "configuration/xrechnung/2.3.1_2023-05-12",\
"-s", "configuration/xrechnung/2.2.0_2022-11-15/scenarios.xml", "-r", "configuration/xrechnung/2.2.0_2022-11-15",\
"-s", "configuration/xrechnung/2.1.1_2021-11-15/scenarios.xml", "-r", "configuration/xrechnung/2.1.1_2021-11-15",\
"-s", "configuration/xrechnung/2.0.1_2020-12-31/scenarios.xml", "-r", "configuration/xrechnung/2.0.1_2020-12-31",\
"-s", "configuration/xrechnung/3.0.2_2024-10-31/scenarios.xml", "-r", "configuration/xrechnung/3.0.2_2024-10-31",\
"-D", "-P", "80", "-H", "0.0.0.0"]
