.PHONY: install build ask app

install:        ## install dependencies
	pip install -r requirements.txt

build:          ## build the sample SQLite database
	python -m src.build_db

ask:            ## ask a question (or demo mode without a key)
	python -m src.cli

app:            ## launch the Streamlit UI
	streamlit run src/app.py
