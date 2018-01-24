.PHONY: dummy

PYTHONPATH := $(CURDIR):test
COVERAGE_DIR := $(CURDIR)/coverage

VPATH = coverage

APP_DIR := $(CURDIR)/apps
APP_PATHS := $(wildcard $(APP_DIR)/*)
APP_PATHS := $(filter-out $(APP_DIR)/__%,$(APP_PATHS))
APP_NAMES := $(notdir $(APP_PATHS))

REQUIREMENTS_PATHS := $(APP_DIR)/requirements*
REQUIREMENTS_FILES := $(notdir $(REQUIREMENTS_PATHS))
REQUIREMENTS_TEMP := $(CURDIR)/temp-requirements.txt
PIP_OUTDATED_TEMP := temp-pip-outdated.txt

venv: dummy
	rm -rf venv
	python3 -m venv --system-site-packages venv
	echo "[global]" > venv/pip.conf
	echo "format = columns" >> venv/pip.conf
	@echo "Virtual env created. Now do: source venv/bin/activate"

lint-server: dummy
	flake8 medley.py
	pylint --rcfile=.pylintrc medley.py;


# Filter the list of outdated packages to direct dependencies
#
# By default, pip returns a list of all outdated packages. It can be
# annoying to reconcile this list to the contents of requirements.txt
# to separate direct dependencies (things this application uses) from
# indirect dependencies (other things used by direct dependencies).
#
# This setup also handles multiple requirements files.
outdated: .pip-outdated $(REQUIREMENTS_FILES)
	rm $(PIP_OUTDATED_TEMP)

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

# Filter the list of outdated packages based on the contents of a requirements file
#
# This is normally called from the outdated target. It greps the temp file produced
# by the .pip-outdated target to avoid slowdown across multiple calls.
#
# The package names are extracted to a temporary file to facilitate grepping. There is
# some sed fiddling with this file to improve the readability of the grep.
#
# Don't invoke directly.
#
$(REQUIREMENTS_FILES): dummy
	@echo ""
	@echo "Outdated packages from $@:"
	@cut -d'=' -f 1 $@ > $(REQUIREMENTS_TEMP)
	@echo "Package" >> $(REQUIREMENTS_TEMP)
	@echo "-------" >> $(REQUIREMENTS_TEMP)
	@-grep -f $(REQUIREMENTS_TEMP) $(PIP_OUTDATED_TEMP)
	@echo ""
	@rm $(REQUIREMENTS_TEMP)

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


# Save pip's list of outdated packages to a temp file.
#
# Don't invoke directly.
#
.pip-outdated: dummy
	pip list --format=columns --not-required --outdated > $(PIP_OUTDATED_TEMP)


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
	coverage report

# Build a coverage report and view the HTML report in a browser
#
# Example: make htmlcov
#
# Uses the macOS-specific open utility to launch the default browser.
htmlcov: coverage
	coverage html
	open htmlcov/index.html



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


vagrant-install: dummy
	vagrant box update
	vagrant up

vagrant-provision: dummy
	vagrant provision


#
# Empty the logindex database and re-index
#
# For use when changes to the logindex or visitors apps require a
# database do-over. Does not handle schema changes because server
# would need to be restarted.
#
logindex-trial: dummy
	sqlite3 db/logindex.sqlite 'delete from logs'
	curl -d "start=2017-12-01" "http://localhost:8085/logindex"
	sleep 1
	sqlite3 db/logindex.sqlite 'select count(*) from logs where ip is null'
