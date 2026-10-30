FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY connectwise_mcp.py .

ENV PYTHONUNBUFFERED=1

# HTTP in the container; override MCP_TRANSPORT to run it on stdio instead.
ENV MCP_TRANSPORT=http
ENV MCP_PORT=3002
EXPOSE 3002

# No curl in the image, so the healthcheck uses the Python already here rather
# than adding an apt layer for one command.
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:3002/health').status==200 else 1)"

CMD ["python", "connectwise_mcp.py"]
