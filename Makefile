
.default: help

.PHONY: help
help:
	@echo "usage:"
	@echo ""
	@echo "setup-venv"
	@echo "   create virtual environment"
	@echo "dev | install-dev"
	@echo "   setup development environment"
	@echo ""
	@echo "test | run-all-tests"
	@echo "   run all tests"
	@echo ""
	@echo "run-doc-tests"
	@echo "   run all tests"
	@echo ""
	@echo "run-all-tests-w-coverage"
	@echo "   run all tests with coverage collection"
	@echo ""
	@echo "lint"
	@echo "   lint the code"
	@echo ""
	@echo "type-check"
	@echo "   check types"
	@echo ""
	@echo "fmt"
	@echo "   run formatter(s)"
	@echo ""
	@echo "check-fmt"
	@echo "   check formatting"
	@echo ""

PLATFORM := ${shell uname -o}
PROJECT := sparv

ifeq (${VIRTUAL_ENV},)
  VENV_NAME = venv
  INVENV = export VIRTUAL_ENV="${VENV_NAME}"; export PATH="${VENV_NAME}/bin:${PATH}"; unset PYTHON_HOME;
else
  VENV_NAME = ${VIRTUAL_ENV}
  INVENV =
endif

${info Platform: ${PLATFORM}}

setup-venv:
	python3 -m venv ${VENV_NAME}
	${VENV_NAME}/bin/pip install wheel

dev: install-dev
install-dev:
	${VENV_NAME}/bin/pip install -e .[dev]

setup-sparv:
	${INVENV} sparv setup

setup-sparv-from-env:
	${INVENV} sparv setup --dir ${SPARV_DATADIR}

.PHONY: test
test: run-all-tests
.PHONY: run-all-tests
run-all-tests:
	${INVENV} pytest

.PHONY: noexternal-tests
noexternal-tests:
	${INVENV} pytest -m noexternal

.PHONY: run-all-tests-w-coverage
run-all-tests-w-coverage:
	${INVENV} pytest -vv --cov=${PROJECT}  --cov-report=xml tests

.PHONY: run-all-tests-w-coverage
run-noexternal-tests-w-coverage:
	${INVENV} pytest -vv --cov=${PROJECT}  --cov-report=xml -m noexternal


