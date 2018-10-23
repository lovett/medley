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

PARSER_DIR := $(CURDIR)/parsers
PARSER_PATHS := $(wildcard $(PARSER_DIR)/[a-z]*.py)
PARSER_PATHS := $(filter-out $(PARSER_DIR)/test_%,$(PARSER_PATHS))
PARSER_PATHS := $(notdir $(PARSER_PATHS))
PARSER_PATHS := $(addprefix parsers/,$(PARSER_PATHS))
PARSER_MODULES := $(basename $(PARSER_PATHS))
PARSER_MODULES := $(notdir $(PARSER_MODULES))
PARSER_MODULES := $(addprefix parsers., $(PARSER_MODULES))

REQUIREMENTS_PATHS := $(APP_DIR)/requirements*
REQUIREMENTS_FILES := $(notdir $(REQUIREMENTS_PATHS))
REQUIREMENTS_TEMP := $(CURDIR)/temp-requirements.txt
PIP_OUTDATED_TEMP := temp-pip-outdated.txt

# Identify a suitable package manager.
#
# This has to consider the OS because apt may exist on macOS as a
# symlink to a Java utility within /System/Library/Frameworks.
UNAME := $(shell uname -s)
ifeq ($(UNAME),Linux)
	USE_APT := $(shell command -v apt 2> /dev/null)
endif
ifeq ($(UNAME),Darwin)
	USE_PKGIN := $(shell command -v pkgin 2> /dev/null)
endif

SHARED_JS_DIR := $(CURDIR)/apps/shared/static/js

# Debugging tool to print the value of a variable.
#
# Example: make print-PLUGIN_DIR
#
print-%:
	@echo $* = $($*)

# Set up a virtualenv
#
# The --system-site-packages flag is not used because it results in a
# venv without pip. Instead, system packages are enabled
# after-the-fact by editing the pyvenv.cfg file.
#
# This results in the best of both worlds: a local copy
# of pip with a predictable name (no confusion about pip vs pip3) and
# access to site packages for faster builds.
#
venv: dummy
	@echo -n "Creating a new virtual environment..."
	@rm -rf venv
	@python3 -m venv venv
	@echo "[global]" > venv/pip.conf
	@echo "format = columns" >> venv/pip.conf
	@sed 's/include-system-site-packages = false/include-system-site-packages = true/' venv/pyvenv.cfg > venv/pyvenv.cfg.tmp
	@mv venv/pyvenv.cfg.tmp venv/pyvenv.cfg
	@echo  "done."
	@echo "Now run: source venv/bin/activate"
	@echo "After that, run: make setup"
	@echo "Also consider running: make hooks"

# Install OS packages.
#
system-packages: dummy
ifdef USE_APT
	sudo apt install libasound2-dev rsync
endif

# Filter the list of outdated Python packages to direct dependencies
#
# By default, pip returns a list of all outdated packages. It can be
# annoying to reconcile this list to the contents of requirements.txt
# to separate direct dependencies (things this application uses) from
# indirect dependencies (other things used by direct dependencies).
#
# This setup also handles multiple requirements files.
#
outdated: .pip-outdated $(REQUIREMENTS_FILES)
	rm $(PIP_OUTDATED_TEMP)

setup: system-packages assets
	pip install --upgrade pip setuptools
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

serve: export BETTER_EXCEPTIONS=1
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
coverage: $(addprefix .coverage., $(APP_NAMES) $(PLUGIN_MODULES) $(PARSER_MODULES))
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
	$(eval PLUGIN=$(notdir $(basename $@)))
	$(eval MODULE=$(addprefix plugins.,$(PLUGIN)))
	COVERAGE_FILE=$(COVERAGE_DIR)/$(MODULE).cov \
	python -m pytest --cov=$(MODULE) --cov-branch  plugins/test_$(PLUGIN).py

# Test a single parser
#
# Example: make parsers/myparser.py
#
# Same setup and rational as for plugin testing.
#
# This target can be invoked directly.
#
$(PARSER_PATHS): $(COVERAGE_DIR) dummy
	$(eval PARSER=$(notdir $(basename $@)))
	$(eval MODULE=$(addprefix parsers.,$(PARSER)))
	COVERAGE_FILE=$(COVERAGE_DIR)/$(MODULE).cov \
	python -m pytest --cov=$(MODULE) --cov-branch  parsers/test_$(PARSER).py

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
	flake8 $(APP_DIR) $(PLUGIN_DIR) $(PARSER_DIR) medley.py
	pylint --rcfile=.pylintrc $(APP_DIR) $(PLUGIN_DIR) $(PARSER_DIR) medley.py


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

# Download third-party front-end assets.
#
# This is deliberately simplistic in order to avoid having to bother
# with Node.js, npm, and the like. This application doesn't need any
# of that.
#
assets: dummy
	curl --silent 'https://vuejs.org/js/vue.js' -o $(SHARED_JS_DIR)/vue.js
	curl --silent 'https://vuejs.org/js/vue.min.js' -o $(SHARED_JS_DIR)/vue.min.js

# Build the application
#
# There isn't a whole lot going on here because there isn't much to
# build. The front-end deliberately doesn't use NPM or anything else
# that involves Node.js.
#
# The one operation that will be done here is to switch from the
# development version of Vue to the production version.
#
build: dummy
	mv $(SHARED_JS_DIR)/vue.min.js $(SHARED_JS_DIR)/vue.js

#
# Create a package upgrade commit.
#
# "puc" stands for Package Upgrade Commit
#
puc: dummy
	git checkout master
	git add requirements.txt requirements-dev.txt
	git commit -m "Upgrade third-party libraries"

# Set up git hooks
#
# This is kept away from other targets like venv and setup so that it
# doesn't interfere with CI. The suggestion printed by the venv target
# is enough of a reminder, given how infrequently this target is
# needed.
#
hooks: dummy
	ln -sf ../../hooks/pre-commit .git/hooks/pre-commit

# Automation for merging changes from the master branch into the
# production branch.
#
master-to-production: dummy
	git checkout production
	git merge master
	git push
	git checkout master
