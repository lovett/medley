.PHONY: dummy

PYTHONPATH := $(CURDIR):test
COVERAGE_DIR := $(CURDIR)/coverage

VPATH = coverage

APP_DIR := $(CURDIR)/apps
APP_PATHS := $(wildcard $(APP_DIR)/*)
APP_PATHS := $(filter-out $(APP_DIR)/__%,$(APP_PATHS))
APP_NAMES := $(notdir $(APP_PATHS))


venv: dummy
	rm -rf venv
	virtualenv -p python3 --no-site-packages --prompt="♪ ♪ ♪" venv
	echo "[global]" > venv/pip.conf
	echo "format = columns" >> venv/pip.conf

lint-server: dummy
	flake8 medley.py
	pylint --rcfile=.pylintrc medley.py;

outdated: dummy
	pip list --outdated

setup: dummy
	pip install --upgrade pip setuptools
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

serve: dummy
	python medley.py


# Create the coverage directory
#
# Don't invoke directly.
#
$(COVERAGE_DIR):
	mkdir $(COVERAGE_DIR)


# Create a coverage file for each app
#
# Don't invoke directly.
#
# Uses an order-only prerequisite to create the coverage directory.
#
%.cov: $(APP_DIR)/%/main.py $(APP_DIR)/%/test.py | $(COVERAGE_DIR)
	PYTHONPATH=$(PYTHONPATH)  COVERAGE_FILE=$(COVERAGE_DIR)/$*.cov \
	coverage run --branch --source $(APP_DIR)/$* --omit $(APP_DIR)/$*/test.py $(APP_DIR)/$*/test.py


# Copy a .cov file to a .coverage file
#
# Don't invoke directly.
#
.coverage.%:
	@if [ -f $(COVERAGE_DIR)/$*.cov ]; then \
	cp $(COVERAGE_DIR)/$*.cov $(COVERAGE_DIR)/.coverage.$*; fi


# Build a coverage report
#
# Example: make coverage
#
# Creates a unifed coverage report for all apps in both CLI and HTML
# formats. Depends on the .coverage.appname target to copy individual
# coverage files to what the coverage utility expects to see.
#
coverage: $(addprefix .coverage., $(APP_NAMES))
	coverage combine $(COVERAGE_DIR)
	coverage html
	coverage report


# Test all apps
#
# Example: make test
#
# A shortcut for calling "make appname" for every app individually, and
# the sort of thing you'd want to invoke during CI.
#
# This will stop at the first failing app, rather than go through
# everything every time.
#
test: $(APP_NAMES)


# Test a single app
#
# Example: make appname
#
# Invokes pytest with the pytest-cov plugin and writes an app-specific
# coverage file to the coverage directory.
#
# The coverage file uses a non-standard name (ex: appname.cov) so
# that report generation is re-reunnable.
#
# If the coverage file had a standard name (ex: .coverage.appname)
# it would get deleted during combination and you'd have to regenerate
# everything else just to reflect changes in one app.
#
$(APP_NAMES): $(COVERAGE_DIR)
	COVERAGE_FILE=$(COVERAGE_DIR)/$@.cov \
	python -m pytest --cov=apps.$@ --cov-branch  $(APP_DIR)/$@
