test:
	python3 -m unittest discover
	./scripts/doctestmod $$(find tm -name '*.py')
