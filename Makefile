.PHONY: dummy
.DEFAULT_GOAL := setup

PYTHONPATH := $(CURDIR):test

# The absolute path to the coverage directory.
COVERAGE_DIR := $(CURDIR)/coverage

# A list of app names in the form "app.[name of app]".
APPS := $(wildcard apps/*)
APPS := $(notdir $(APPS))
APPS := $(filter-out __%,$(APPS))
APPS := $(addprefix apps., $(APPS))

# A list of parsers with test suites in the form "parsers.[name of parser]".
PARSERS := $(wildcard parsers/*_test.py)
PARSERS := $(notdir $(PARSERS))
PARSERS := $(basename $(PARSERS))
PARSERS := $(subst _test,,$(PARSERS))
PARSERS := $(addprefix parsers., $(PARSERS))

# A list of plugins with test suites in the form "plugins.[name of plugin]".
PLUGINS := $(wildcard plugins/*_test.py)
PLUGINS := $(notdir $(PLUGINS))
PLUGINS := $(basename $(PLUGINS))
PLUGINS := $(subst _test,,$(PLUGINS))
PLUGINS := $(addprefix plugins., $(PLUGINS))

REQUIREMENTS_PATHS := $(APP_DIR)/requirements*
REQUIREMENTS_FILES := $(notdir $(REQUIREMENTS_PATHS))
REQUIREMENTS_TEMP := $(CURDIR)/temp-requirements.txt
PIP_OUTDATED_TEMP := temp-pip-outdated.txt

SHARED_JS_DIR := $(CURDIR)/apps/shared/static/js
FAVICON_DIR := $(CURDIR)/apps/shared/static/favicon
TMUX_SESSION_NAME := medley

vpath %.cov coverage

export PATH := ./venv/bin:$(PATH)

# Make utility to print the value of a variable for debugging
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
# This results in the best of both worlds: a local copy of pip with a
# predictable name (no confusion about pip vs pip3) and access to site
# packages for faster builds.
#
# Although the documentation for Python 3.5 says that pip is installed
# by default, this doesn't appear to be the case at the moment on
# Raspbian Stretch. Fiddling with pyenv.cfg is a workaround.
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


# Install third-party Python libraries
#
setup: dummy
	pip install --upgrade pip setuptools
	pip install -r requirements.txt
	pip install -r requirements-dev.txt


# Install simpleaudio, an additional library for wav file playback
#
# This is an optional step that is separate from the main setup target
# because it can be a hassle to build. On Debian you'll need to have the
# libasound2-dev package installed.
#
# The non-audio parts of medley work fine without this library.
#
setup-audio:
	pip install -r requirements-audio.txt

# Run a local development webserver
#
serve: dummy
	python medley.py


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


# Quietly rename coverage files to comply with coverage utility's
# expectations.
#
# Coverage files start out with a .cov suffix, but the coverage
# reporter needs a different naming convention.
.coverage.%:
	@-cp $(COVERAGE_DIR)/$*.cov $(COVERAGE_DIR)/.coverage.$*


# Save pip's list of outdated packages to a temp file.
.pip-outdated: dummy
	pip list --format=columns --outdated > $(PIP_OUTDATED_TEMP)


# Build a coverage report for all available coverage files.
#
# This rule merges the indiviual files within the coverage directory
# into a master .coverage file at the project root.
#
# Two reports are generated: a plain-text version for the command line
# and an HTML version stored in the static directory of the coverage app.
#
# The merging process will remove the intermediate .coverage files,
# making this rule ineligible for skipping.
coverage: $(addprefix .coverage., $(APPS) $(PLUGINS) $(PARSERS))
	coverage combine $(COVERAGE_DIR)
	coverage report
	coverage html -d apps/coverage/static


# Run the tests for everything.
test: $(APPS) $(PARSERS) $(PLUGINS) coverage

# Generate test coverage for a single app.
#
# This is a pattern rule based on the coverage file generated by pytest.
#
# Its target is the file coverage/apps.[name of app]/cov
#
# Its prerequesites are the application's main.py and its test file.
#
# Customizing the name of the coverage file allows Make to skip the
# tests if nothing has changed. This is also why the coverage file is
# deleted if the tests fail.
apps.%.cov: apps/%/main.py apps/%/main_test.py
	mkdir -p $(COVERAGE_DIR)
	COVERAGE_FILE=coverage/$@ \
	python -m pytest --cov=apps.$* --cov-branch apps/$* \
	|| (rm $(COVERAGE_DIR)/$@ && exit 1)

# Generate test coverage for a single parser.
#
# This is a pattern rule based on the coverage file generated by pytest.
#
# Its target is a file coverage/parsers.[name of parser].cov
#
# Its prerequisites are the parser class and its test file.
#
# Customizing the name of the coverage file allows Make to skip the
# tests if nothing has changed. This is also why the coverage file is
# deleted if the tests fail.
parsers.%.cov: parsers/%.py parsers/%_test.py
	mkdir -p $(COVERAGE_DIR)
	COVERAGE_FILE=coverage/$@ \
	python -m pytest --cov=parsers.$* --cov-branch parsers/$*_test.py \
	|| (rm $(COVERAGE_DIR)/$@ && exit 1)

# Generate test coverage for a single plugin.
#
# This is a pattern rule based on the coverage file generated by pytest.
#
# Its target is a file coverage/plugins.[name of parser].cov
#
# Its prerequisites are the plugin class and its test file.
#
# Customizing the name of the coverage file allows Make to skip the
# tests if nothing has changed. This is also why the coverage file is
# deleted if the tests fail.
plugins.%.cov: plugins/%.py plugins/%_test.py
	mkdir -p $(COVERAGE_DIR)
	COVERAGE_FILE=coverage/$@ \
	python -m pytest --cov=plugins.$* --cov-branch plugins/$*_test.py \
	|| (rm $(COVERAGE_DIR)/$@ && exit 1)


# Test a single app.
#
# This rule is a shortcut for the "apps.%.cov" pattern rule so that
# the ".cov" suffix can be omitted.
$(APPS):
	@$(MAKE) --no-print-directory $@.cov


# Test a single parser
#
# This rule is a shortcut for the "parsers.%.cov" pattern rule so that
# the ".cov" suffix can be omitted.
$(PARSERS):
	@$(MAKE) --no-print-directory $@.cov


# Test a single plugin
#
# This rule is a shortcut for the "plugins.%.cov" pattern rule so that
# the ".cov" suffix can be omitted.
$(PLUGINS):
	@$(MAKE) --no-print-directory $@.cov


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
	flake8 --builtins=ModuleNotFoundError $(APP_DIR) $(PLUGIN_DIR) $(PARSER_DIR) medley.py
	pylint --rcfile=.pylintrc $(APP_DIR) $(PLUGIN_DIR) $(PARSER_DIR) medley.py


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
assets: assets-vue assets-flags


# Asset download of Vue.js without using npm
#
# This is deliberately simplistic in order to avoid dependency on
# Node, which would otherwise be overkill for this application's
# needs.
#
assets-vue: dummy
	curl --silent 'https://vuejs.org/js/vue.js' -o $(SHARED_JS_DIR)/vue.js
	curl --silent 'https://vuejs.org/js/vue.min.js' -o $(SHARED_JS_DIR)/vue.min.js


# Asset download of flag-icon-css library used in visitors app
#
# Similar to how Vue is handled, this is a direct-download approach
# rather than an npm-based approach. The files used by the visitors
# app are a subset of what the project provides.
#
assets-flags: dummy
	rm -fr master.zip apps/visitors/static/flag-icon-css/flags/4x3
	curl --silent -L -O 'https://github.com/lipis/flag-icon-css/archive/master.zip'
	unzip master.zip
	mv flag-icon-css-master/flags/4x3 apps/visitors/static/flag-icon-css/flags/
	mv flag-icon-css-master/css/flag-icon.min.css apps/visitors/static/flag-icon-css/css/
	mv flag-icon-css-master/LICENSE apps/visitors/static/flag-icon-css/LICENSE
	rm -rf master.zip flag-icon-css-master


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


# Create a package upgrade commit.
#
puc: dummy
	git checkout master
	git add requirements.txt requirements-dev.txt
	git commit -m "Upgrade third-party libraries"


# Set up git hooks
#
# This is independent of other targets like venv and setup so that it
# doesn't interfere with CI. The suggestion printed by the venv target
# is enough of a reminder, given how infrequently this target is
# needed.
#
hooks: dummy
	ln -sf ../../hooks/pre-commit .git/hooks/pre-commit


favicon: dummy
	convert $(FAVICON_DIR)/app-icon.png -geometry 48x48 temp-48.png
	convert $(FAVICON_DIR)/app-icon.png -geometry 32x32 temp-32.png
	convert $(FAVICON_DIR)/app-icon.png -geometry 16x16 temp-16.png
	convert temp-16.png temp-32.png temp-48.png apps/shared/static/favicon/favicon.ico
	rm temp-48.png temp-32.png temp-16.png
	convert $(FAVICON_DIR)/app-icon.png -density 600 -geometry 76x76 $(FAVICON_DIR)/app-icon-76.png
	convert $(FAVICON_DIR)/app-icon.png -geometry 144x144 $(FAVICON_DIR)/app-icon-144.png
	convert $(FAVICON_DIR)/app-icon.png -geometry 180x180 $(FAVICON_DIR)/app-icon-180.png
	cd $(FAVICON_DIR) && optipng -quiet -o 3 *.png

# Automation for merging changes from the master branch into the
# production branch.
#
master-to-production: dummy
	git checkout master
	git push
	git checkout production
	git merge master
	git push
	git checkout master


# Automation for setting up a tmux session
#
workspace:
# 0: Editor
	tmux new-session -d -s "$(TMUX_SESSION_NAME)" bash
	tmux send-keys -t "$(TMUX_SESSION_NAME)" "$(EDITOR) ." C-m

# 1: Shell
	tmux new-window -a -t "$(TMUX_SESSION_NAME)" bash
	tmux send-keys -t "$(TMUX_SESSION_NAME)" "source venv/bin/activate" C-m

# 2: Dev server
	tmux new-window -a -t "$(TMUX_SESSION_NAME)" -n "devserver" "source venv/bin/activate; make serve"

	tmux select-window -t "$(TMUX_SESSION_NAME)":0
	tmux attach-session -t "$(TMUX_SESSION_NAME)"

# Install the application on the production host via Ansible
install:
	ansible-playbook ansible/install.yml

# Perform sundry cleanup tasks.
reset:
	rm -r coverage
	rm -r htmlcov
	rm .coverage
