.PHONY: dummy

NOTIFIER := /usr/local/bin/send-notification
PYTHONPATH := $(CURDIR):test
COVERAGE_DIR := $(CURDIR)/coverage

VPATH = coverage

APP_DIR := $(CURDIR)/apps
APP_PATHS := $(wildcard $(APP_DIR)/*)
APP_PATHS := $(filter-out $(APP_DIR)/__%,$(APP_PATHS))
APP_NAMES := $(notdir $(APP_PATHS))


define notify
	$(NOTIFIER) -t "$1" -p 0
endef

install: dummy
	ansible-playbook ansible/install.yml
	$(call notify,Medley install complete)

update: dummy
	ansible-playbook ansible/update.yml
	$(call notify,Medley update complete)

venv: dummy
	rm -rf venv
	virtualenv -p python3 --no-site-packages --prompt="♪ ♪ ♪" venv

setup: dummy
	pip install --upgrade pip setuptools
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

serve: dummy
	python medley.py


# Create the coverage directory
$(COVERAGE_DIR):
	mkdir $(COVERAGE_DIR)

# Create a coverage file for each app
#
# Uses an order-only prerequisite to create the coverage directory.
%.cov: $(APP_DIR)/%/main.py $(APP_DIR)/%/test.py | $(COVERAGE_DIR)
	PYTHONPATH=$(PYTHONPATH)  COVERAGE_FILE=$(COVERAGE_DIR)/$*.cov \
	coverage run --branch --source $(APP_DIR)/$* --omit $(APP_DIR)/$*/test.py $(APP_DIR)/$*/test.py

# Make per-app coverage files combinable
#
# Per-app coverage files are combined into a single file. This allows a
# single report to describe everything, instead of needing one report
# per app.
#
# Combining deletes the original files, which would force make to
# re-run tests unnecessarily. Combining also hinges on pre-set file
# name conventions.
#
# Copying files makes them recognizable and disposable while keeping
# the originals intact.
.coverage.%: %.cov
	cp $(COVERAGE_DIR)/$*.cov $(COVERAGE_DIR)/.coverage.$*


# Generate a HTML coverage report
htmlcov: $(addprefix .coverage., $(APP_NAMES))
	rm -f .coverage
	rm -rf htmlcov
	coverage combine $(COVERAGE_DIR)
	coverage html

coverage: $(addprefix .coverage., $(APP_NAMES))
	rm -f .coverage
	rm -rf htmlcov
	coverage combine $(COVERAGE_DIR)
	coverage report
