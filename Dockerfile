FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .[all]

# Default: run the all-in-one server
CMD ["dvmcp", "--difficulty", "beginner"]
