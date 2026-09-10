FROM adfreiburg/qlever:0.6.0

USER root

RUN mkdir /index
WORKDIR /index
VOLUME ["/index"]

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 7001
ENTRYPOINT ["/entrypoint.sh"]
