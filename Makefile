.PHONY : docs
docs :
	rm -rf docs/build/
	sphinx-autobuild -b html --watch km2arec/ docs/source/ docs/build/

.PHONY : run-checks
run-checks :
	ruff format --check .
	ruff check .
	CUDA_VISIBLE_DEVICES='' pytest -v --color=yes tests/

.PHONY : format
format :
	ruff format .
	ruff check --fix .

.PHONY : build
build :
	rm -rf *.egg-info/
	python -m build
