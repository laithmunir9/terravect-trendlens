FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TRENDLENS_PUBLIC=1
COPY requirements-public.txt ./
RUN pip install --no-cache-dir -r requirements-public.txt && useradd --create-home --uid 10001 trendlens
COPY app.py analysis.py charts.py dashboard.py data_sources.py demos.py giovanni.py giovanni_snapshot.py insights.py release.py ./
COPY .streamlit/config.toml .streamlit/config.toml
COPY data/demos/abu_dhabi_source.json data/demos/oslo_source.json data/demos/manifest.json data/demos/README.md ./data/demos/
COPY data/demos/giovanni_manifest.json data/demos/giovanni_abu_dhabi_2001_2025.csv data/demos/giovanni_abu_dhabi_2020.csv ./data/demos/
COPY docs/GIOVANNI_ACQUISITION.md ./docs/
COPY LICENSE README.md THIRD_PARTY_NOTICES.md AI_USE.md ./
USER trendlens
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)"
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
