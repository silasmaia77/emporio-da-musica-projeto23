FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd -m appuser
COPY --chown=appuser:appuser . .
RUN mkdir -p data/processed && chown -R appuser:appuser /app
USER appuser
EXPOSE 8501 8000
CMD ["sh", "-c", "python -m src.data.importer && streamlit run app.py --server.address=0.0.0.0"]
