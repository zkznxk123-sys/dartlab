FROM python:3.12-slim

WORKDIR /app

# 빌드 도구 (lxml 등)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# 소스 복사 (LICENSE + PROJECT_README — hatchling 빌드 필수)
COPY pyproject.toml uv.lock LICENSE ./
COPY PROJECT_README.md README.md
COPY src/ src/

# 설치
RUN uv pip install --system .

ENV SPACE_ID=eddmpython/dartlab
ENV DARTLAB_MCP_HTTP=1
ENV DARTLAB_CORS_ORIGINS=*
ENV DARTLAB_HOST=0.0.0.0
ENV DARTLAB_PORT=7860

EXPOSE 7860

CMD ["python", "-m", "dartlab.server"]
