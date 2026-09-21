.PHONY: setup run test eval ui paper ablation prepare

setup:
	python -m venv .venv
	.venv/Scripts/python -m pip install --upgrade pip
	.venv/Scripts/python -m pip install -r requirements.txt

run:
	python -m sda.cli --text "boli me grlo i imam temperaturu 38" --no-embeddings

test:
	pytest -q

eval:
	python scripts/run_eval.py --no-embeddings

ablation:
	python scripts/ablation.py --no-embeddings

prepare:
	python scripts/prepare_data.py

ui:
	streamlit run src/sda/ui/streamlit_app.py

paper:
	@if exist paper\rad.md (echo paper OK: paper\rad.md) else (echo NEDOSTAJE paper\rad.md && exit 1)
