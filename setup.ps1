# Create data directories
New-Item -ItemType Directory -Force -Path data\uploads
New-Item -ItemType Directory -Force -Path data\index
New-Item -ItemType File -Force -Path data\uploads\.gitkeep
New-Item -ItemType File -Force -Path data\index\.gitkeep

# Create logs directory
New-Item -ItemType Directory -Force -Path logs

Write-Host "Setup complete! Next steps:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Update .env with your OpenAI API key and settings"
Write-Host "2. Start infrastructure: docker compose up -d"
Write-Host "3. Install Python dependencies: pip install -r requirements.txt"
Write-Host "4. Start FastAPI: python -m uvicorn app.main:app --reload"
Write-Host "5. Start Celery worker: celery -A app.infra.queue.celery_app worker --loglevel=info"
Write-Host ""
Write-Host "Check http://localhost:8000/docs for API documentation"
