FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
ENV HOME=/app
COPY . .
RUN python -c "from mcp_server.florida_regulations_server import _get_collection; c = _get_collection(); c.query(query_texts=['warm up embedding model'], n_results=1)"
CMD exec uvicorn api:app --host 0.0.0.0 --port $PORT
