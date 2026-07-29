FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml .
COPY mcp-servers/markdown-server/pyproject.toml mcp-servers/markdown-server/
COPY mcp-servers/github-server/pyproject.toml mcp-servers/github-server/
COPY mcp-servers/graph-server/pyproject.toml mcp-servers/graph-server/

RUN uv sync

COPY . .

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
