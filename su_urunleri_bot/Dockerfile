ARG BUILD_FROM
FROM $BUILD_FROM

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    tzdata

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt /app/
RUN python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY . /app/

RUN chmod a+x /app/run.sh

ENV PYTHONUNBUFFERED=1

CMD [ "/app/run.sh" ]
