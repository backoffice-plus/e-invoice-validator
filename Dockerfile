FROM eclipse-temurin:21-jre-jammy@sha256:d63bd8d9b171999cbed8576f2c76e874dd4856791a358536e5c4d407e77edc13

ARG KOSIT_VALIDATOR_VERSION=1.6.2
ARG KOSIT_VALIDATOR_SHA256=244978514ad48f67c7573acfffc8f4fd73d81feda6f276710033f9913579857e

WORKDIR /java-app

RUN curl --fail --location --retry 3 \
      --output validator-standalone.jar \
      "https://github.com/itplr-kosit/validator/releases/download/v${KOSIT_VALIDATOR_VERSION}/validator-${KOSIT_VALIDATOR_VERSION}-standalone.jar" && \
    echo "${KOSIT_VALIDATOR_SHA256}  validator-standalone.jar" | sha256sum --check --strict

COPY configuration /java-app/configuration

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=10 \
  CMD curl -fsS http://127.0.0.1:80/server/health | grep -q "<ns2:status>UP</ns2:status>"

CMD ["java", "-jar", "validator-standalone.jar", \
  "-s", "configuration/factur-x/1.09/scenarios.xml", "-r", "configuration/factur-x/1.09", \
  "-s", "configuration/xrechnung/2.3.1_2023-05-12/scenarios.xml", "-r", "configuration/xrechnung/2.3.1_2023-05-12", \
  "-s", "configuration/xrechnung/2.2.0_2022-11-15/scenarios.xml", "-r", "configuration/xrechnung/2.2.0_2022-11-15", \
  "-s", "configuration/xrechnung/2.1.1_2021-11-15/scenarios.xml", "-r", "configuration/xrechnung/2.1.1_2021-11-15", \
  "-s", "configuration/xrechnung/2.0.1_2020-12-31/scenarios.xml", "-r", "configuration/xrechnung/2.0.1_2020-12-31", \
  "-s", "configuration/xrechnung/3.0.2_2026-01-31/scenarios.xml", "-r", "configuration/xrechnung/3.0.2_2026-01-31", \
  "-D", "-P", "80", "-H", "0.0.0.0", "--disable-gui"]
