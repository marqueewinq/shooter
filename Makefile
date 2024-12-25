.PHONY: diagrams
diagrams:
	PYTHONPATH=./ python docs/generate_diagrams.py

.PHONY: build
build:
	echo "Cleaning up the cache"
	rm -rf dist build/ *.egg-info
	echo "Building tar + whl"
	python -m build

.PHONY: install
install:
	pip install -e .

.PHONY: run
run:
	PYTHONPATH=./ python shooter/app.py --host 127.0.0.1 --port 8000

.PHONY: e2e_test
e2e_test:
	bash test.sh 127.0.0.1 8000

.PHONY: unit_test
unit_test:
	PYTHONPATH=./ pytest . --cov=shooter --cov-report=html --durations=3 -vvv

.PHONY: output
output:
	mkdir ./output
	echo "*\n!.gitignore" > ./output/.gitignore
