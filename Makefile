.PHONY: dummy
.DEFAULT_GOAL := setup

PYTHONPATH := $(CURDIR):test
COVERAGE_DIR := $(CURDIR)/coverage

VPATH = coverage

APP_DIR := $(CURDIR)/apps
APP_PATHS := $(wildcard $(APP_DIR)/*)
APP_PATHS := $(filter-out $(APP_DIR)/__%,$(APP_PATHS))
APP_NAMES := $(notdir $(APP_PATHS))

PLUGIN_DIR := $(CURDIR)/plugins
PLUGIN_PATHS := $(wildcard $(PLUGIN_DIR)/[a-z]*.py)
PLUGIN_PATHS := $(filter-out $(PLUGIN_DIR)/test_%,$(PLUGIN_PATHS))
PLUGIN_PATHS := $(notdir $(PLUGIN_PATHS))
PLUGIN_PATHS := $(addprefix plugins/,$(PLUGIN_PATHS))
PLUGIN_MODULES := $(basename $(PLUGIN_PATHS))
PLUGIN_MODULES := $(notdir $(PLUGIN_MODULES))
PLUGIN_MODULES := $(addprefix plugins., $(PLUGIN_MODULES))

REQUIREMENTS_PATHS := $(APP_DIR)/requirements*
REQUIREMENTS_FILES := $(notdir $(REQUIREMENTS_PATHS))
REQUIREMENTS_TEMP := $(CURDIR)/temp-requirements.txt
PIP_OUTDATED_TEMP := temp-pip-outdated.txt

# Debugging tool to print the value of a variable.
#
# Example: make print-PLUGIN_DIR
#
print-%:
	@echo $* = $($*)

venv: dummy
	rm -rf venv
	python3 -m venv --system-site-packages venv
	echo "[global]" > venv/pip.conf
	echo "format = columns" >> venv/pip.conf
	@echo "Virtual env created. Now do: source venv/bin/activate"

# Filter the list of outdated packages to direct dependencies
#
# By default, pip returns a list of all outdated packages. It can be
# annoying to reconcile this list to the contents of requirements.txt
# to separate direct dependencies (things this application uses) from
# indirect dependencies (other things used by direct dependencies).
#
# This setup also handles multiple requirements files.
#
# Use of "or true" after the npm outdated command prevents a non-zero
# exit code from producing a warning. Non-zero exit here is ok.
outdated: .pip-outdated $(REQUIREMENTS_FILES)
	rm $(PIP_OUTDATED_TEMP)
	npm outdated || true

setup: dummy
	pip install --upgrade pip setuptools
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	npm install -D --no-optional

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
# Creates a unified coverage report for all apps and plugins.
#
# The unified report is built indirectly from the .cov files in the
# coverage directory.
#
coverage: $(addprefix .coverage., $(APP_NAMES) $(PLUGIN_MODULES))
	coverage combine $(COVERAGE_DIR)
	coverage report
	coverage html


# Test all apps
#
# Example: make test
#
# A shortcut for calling "make appname" for every app individually, and
# the sort of thing you'd want to invoke during CI.
#
# This will stop at the first failing app.
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
# that report generation is re-runnable.
#
# If the coverage file had a standard name (ex: .coverage.appname)
# it would get deleted during combination and you'd have to regenerate
# everything else just to reflect changes in one app.
#
# This target can be invoked directly. It is also invoked by the Git
# pre-commit hook.
#
$(APP_NAMES): $(COVERAGE_DIR)
	COVERAGE_FILE=$(COVERAGE_DIR)/$@.cov \
	python -m pytest --cov=apps.$@ --cov-branch  $(APP_DIR)/$@


# Test a single plugin
#
# Example: make plugins/myplugin.py
#
# Invokes pytest with the pytest-cov plugin and writes a plugin-specific
# coverage file to the coverage directory.
#
# The coverage file uses a non-standard name (ex: plugins.myplugin.cov) so
# that report generation is re-runnable.
#
# If the coverage file had a standard name (ex:
# .coverage.plugins.myplugin) it would get deleted during combination
# and you'd have to regenerate everything else just to reflect changes
# in one plugin.
#
# This target can be invoked directly.
#
$(PLUGIN_PATHS): $(COVERAGE_DIR)
	$(eval MODULE=$(addprefix plugins.,$(notdir $(basename $@))))
	COVERAGE_FILE=$(COVERAGE_DIR)/$(MODULE).cov \
	python -m pytest --cov=$(MODULE) --cov-branch  $@


# Run lint checks across the project
#
# This will consider plugins app controllers and their tests, and the
# main server file.
#
# Two linters are used for the sake of being comprehensive.
#
# These commands are also present in the Git pre-commit hook, but
# are only applied to changed files.
#
lint: dummy
	flake8 $(APP_DIR) $(PLUGIN_DIR) medley.py
	pylint --rcfile=.pylintrc $(APP_DIR) $(PLUGIN_DIR) medley.py


vagrant-install: dummy
	vagrant box update
	vagrant up

vagrant-provision: dummy
	vagrant provision


# Empty the logindex database and re-index
#
# For use when changes to the logindex or visitors apps require a
# database do-over.
#
logindex-reset: dummy
	rm db/logindex.sqlite
	touch medley.py

# Copy front-end assets from node_modules into apps/shared/static.
#
# Deliberately simplistic, and only needs to be run after an npm
# upgrade.
#
assets: JS_DIR := apps/shared/static/js/
assets: export NPM_CONFIG_PROGRESS = false
assets: dummy
	cp node_modules/vue/dist/vue.js $(JS_DIR)
	cp node_modules/vue/dist/vue.min.js $(JS_DIR)

#
# Build the application
#
build: assets

#
# Create a package upgrade commit.
#
# "puc" stands for Package Upgrade Commit
#
puc: dummy
	git checkout master
	git add requirements.txt requirements-dev.txt package.json package-lock.json
	git commit -m "Upgrade pip and npm packages"

#
# Set up git hooks
#
hooks: dummy
	ln -sf ../../hooks/pre-commit .git/hooks/pre-commit
