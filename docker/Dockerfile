FROM python:3.12-slim

ARG INSTALL="snippet-cli==2.3.3"
COPY dist/ /tmp/dist/
RUN pip install /tmp/dist/${INSTALL} 2>/dev/null || pip install ${INSTALL}

COPY docker/test.sh /usr/local/bin/test.sh
RUN chmod +x /usr/local/bin/test.sh

ENTRYPOINT ["snippet"]