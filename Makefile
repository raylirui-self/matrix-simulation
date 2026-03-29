.PHONY: install dev test run dashboard dashboard-legacy sweep clean construct api frontend

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v

run:
	python main.py new && python main.py run --ticks 500

# ── The Construct (new frontend) ──
api:
	uv run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

construct:
	@echo "Start the backend and frontend in separate terminals:"
	@echo "  Terminal 1: make api"
	@echo "  Terminal 2: make frontend"
	@echo ""
	@echo "Then open http://localhost:5173"

# ── Legacy Streamlit dashboard ──
dashboard-legacy:
	streamlit run dashboard_legacy.py

dashboard:
	streamlit run dashboard.py

sweep:
	python sweep.py --param environment.harshness --values 0.5,1.0,1.5,2.0 --ticks 200

clean:
	rm -f output/simulation.db output/test_persistence.db
	rm -rf output/export_*
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
