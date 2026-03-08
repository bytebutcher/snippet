.PHONY: install install-test test test-integration test-integration-quick build publish-test publish clean

install:
	pip install -e .

install-test:
	pip install -e .[test]

test:
	python test.py

test-integration: clean build
	sudo docker build -f docker/Dockerfile --build-arg INSTALL="snippet_cli-*.*.*-py3-none-any.whl" -t snippet-cli .
	sudo docker run -it --rm --entrypoint test.sh snippet-cli

test-integration-quick:
	chmod +x docker/test.sh
	sudo docker run -it --rm \
		-v $(PWD)/docker:/docker \
		--entrypoint /docker/test.sh snippet-cli

build:
	pip3 install build --quiet
	pip install --upgrade twine --quiet
	python3 -m build
	twine check dist/*

publish-test: clean build test test-integration
	twine upload -r testpypi dist/*

publish: clean build test test-integration
	twine upload dist/*

clean:
	rm -rf build/ src/*.egg-info/ dist/