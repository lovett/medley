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

# A list of app-specific icons.
APP_ICONS := $(wildcard apps/*/static/app-icon.svg)
APP_ICONS := $(patsubst %.svg,%.png,$(APP_ICONS))

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

# A list of resources with test suites in the form "resources.[name of resource]".
RESOURCES := $(wildcard resources/*_test.py)
RESOURCES := $(notdir $(RESOURCES))
RESOURCES := $(basename $(RESOURCES))
RESOURCES := $(subst _test,,$(RESOURCES))
RESOURCES := $(addprefix resources., $(RESOURCES))

SHARED_JS_DIR := $(CURDIR)/apps/static/js

TMUX_SESSION_NAME := medley

VENV_ACTIVATE := venv/bin/activate$(PYTHON_VENV_ACTIVATE_EXTENSION)

vpath %.cov coverage

export PATH := ./venv/bin:$(PATH)

# Make utility to print the value of a variable for debugging
#
# Example: make print-PLUGIN_DIR
print-%:
	@echo $* = $($*)


# Set up a virtualenv
#
# The sed command fixes an error with fish shell during sourcing.
#
# See https://github.com/pypa/virtualenv/pull/1379/commits
venv:
	@echo "Creating a new virtual environment..."
	@python3 -m venv --system-site-packages venv
	@sed -i'' 's/$$_OLD_FISH_PROMPT_OVERRIDE"$$/$$_OLD_FISH_PROMPT_OVERRIDE" \&\& functions -q _old_fish_prompt/' venv/bin/activate.fish

# Install third-party Python libraries
setup: venv
	./venv/bin/python -m pip install --quiet --upgrade pip setuptools
	./venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt

# Install dev-specific third-party Python libraries
#
# This is isolated from the setup target for the benefit of CI, where
# dev packages are unused.
setup-dev: setup
	./venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements-dev.txt

# Build the application as a zipapp
medley: setup
	rsync -a --filter='merge .rsync-build-filters' --delete --delete-excluded . build/
	mv build/medley.py build/__main__.py
	./venv/bin/python -m compileall -j 0 -q build
	./venv/bin/python -m pip install --compile \
		--disable-pip-version-check \
		--no-color \
		--quiet \
		-r requirements.txt \
		--target build \
		--upgrade
	find build -depth -type d -name '*.dist-info' -exec rm -rf {} \;
	find build -depth -type d -name 'test*' -exec rm -rf {} \;
	python -m zipapp -p "/usr/bin/env python3" -o medley build
	./medley --publish

# Install the application on the production host
install: medley
	ansible-playbook --skip-tags "firstrun" ansible/install.yml

# Run a local development webserver.
#
# The entr utility ensures the server can be restarted if there is a
# fatal error like bad syntax. It is a backup for CherryPy's autoreload.
serve: export MEDLEY_autoreload=True
serve: export MEDLEY_memorize_hashes=False
serve: export MEDLEY_etags=True
serve: export MEDLEY_tracebacks=True
serve: export MEDLEY_prefetch=False
serve:
	ls apps/**/main.py plugins/*.py tools/*.py parsers/*.py medley.py | entr python medley.py

# A temporary target to help with building out mypy stubs
stubdev:
	ls apps/**/*.py | entr mypy apps

# Profile function calls.
profile:
	python -m cProfile -o medley.prof medley.py

# Profile memory usage.
profilemem:
	mprof run  --include-children --multiprocess medley.py

# Display profiled memory usage.
profilestats:
	echo 'sort cumtime\nstats' | python -m pstats medley.prof | less

# Rename coverage files to comply with coverage utility's
# expectations.
#
# Coverage files start out with a .cov suffix, but the coverage
# reporter needs a different naming convention.
.coverage.%:
	@-cp $(COVERAGE_DIR)/$*.cov $(COVERAGE_DIR)/.coverage.$*


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
coverage: $(addprefix .coverage., $(APPS) $(PLUGINS) $(PARSERS) $(RESOURCES))
	coverage combine $(COVERAGE_DIR)
	coverage report
	coverage html -d apps/static/coverage
	curl -X DELETE 'http://localhost:8085/maintenance/memorize'


# Run the tests for everything.
test: $(APPS) $(PARSERS) $(PLUGINS) $(RESOURCES) coverage


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
	python -m pytest --cov-config=.coveragerc --cov=apps.$* apps/$* \
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
	python -m pytest  --cov-config=.coveragerc --cov=parsers.$* parsers/$*_test.py \
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
	python -m pytest --cov-config=.coveragerc --cov=plugins.$* plugins/$*_test.py \
	|| (rm $(COVERAGE_DIR)/$@ && exit 1)

# Generate test coverage for a single resource.
#
# This is a pattern rule based on the coverage file generated by pytest.
#
# Its target is a file coverage/resources.[name of parser].cov
#
# Its prerequisites are the plugin class and its test file.
#
# Customizing the name of the coverage file allows Make to skip the
# tests if nothing has changed. This is also why the coverage file is
# deleted if the tests fail.
resources.%.cov: resources/%.py resources/%_test.py
	mkdir -p $(COVERAGE_DIR)
	COVERAGE_FILE=coverage/$@ \
	python -m pytest --cov-config=.coveragerc --cov=resources.$* resources/$*_test.py \
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

# Test a single resource
#
# This rule is a shortcut for the "resources.%.cov" pattern rule so that
# the ".cov" suffix can be omitted.
$(RESOURCES):
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
lint: dummy
	mypy --html-report apps/static/mypy apps parsers plugins testing tools medley.py
	flake8 --builtins=ModuleNotFoundError apps parsers plugins testing tools medley.py
	pylint --rcfile=.pylintrc apps parsers plugins testing tools medley.py


# Empty the logindex database and re-index
#
# For use when changes to the logindex or visitors apps require a
# database do-over.
logindex-reset: dummy
	rm db/logindex.sqlite
	touch medley.py


# Download third-party front-end assets.
#
assets: assets-flags


# Asset download of flag-icon-css library used in visitors app
#
# These files are used in the visitors app, but only a subset of what
# the project offers is needed.
assets-flags: dummy
	rm -rf master.zip apps/static/flag-icon-css
	curl --max-time 10 --silent -L -O 'https://github.com/lipis/flag-icon-css/archive/master.zip'
	unzip master.zip
	mkdir -p apps/static/flag-icon-css/flags/4x3
	mkdir -p apps/static/flag-icon-css/css
	mv flag-icon-css-master/flags/4x3 apps/static/flag-icon-css/flags/
	mv flag-icon-css-master/css/flag-icon.min.css apps/static/flag-icon-css/css/
	mv flag-icon-css-master/LICENSE apps/static/flag-icon-css/LICENSE
	rm -rf master.zip flag-icon-css-master

# Set up git hooks
#
# This is independent of other targets like venv and setup so that it
# doesn't interfere with CI. The suggestion printed by the venv target
# is enough of a reminder, given how infrequently this target is
# needed.
hooks: dummy
	ln -sf ../../hooks/pre-commit .git/hooks/pre-commit


# Build the application favicon.
favicon: dummy
	convert -density 900 -background none -geometry 48x48 apps/static/app-icon.svg temp-48.png
	convert -density 900 -background none -geometry 32x32 apps/static/app-icon.svg temp-32.png
	convert -density 900 -background none -geometry 16x16 apps/static/app-icon.svg temp-16.png
	convert temp-16.png temp-32.png temp-48.png apps/static/favicon.ico
	rm temp-48.png temp-32.png temp-16.png
	cd apps/static && optipng -quiet -o 3 *.png


# Automation for setting up a tmux session
workspace:
# 0: Editor
	tmux new-session -d -s "$(TMUX_SESSION_NAME)" "$$SHELL"
	tmux send-keys -t "$(TMUX_SESSION_NAME)" "$(EDITOR) ." C-m

# 1: Shell
	tmux new-window -a -t "$(TMUX_SESSION_NAME)" "$$SHELL"
	tmux send-keys -t "$(TMUX_SESSION_NAME)" "source $(VENV_ACTIVATE)" C-m

# 2: Dev server
	tmux new-window -a -t "$(TMUX_SESSION_NAME)" -n "devserver" "source $(VENV_ACTIVATE); make serve"
	tmux select-window -t "$(TMUX_SESSION_NAME)":0
	tmux attach-session -t "$(TMUX_SESSION_NAME)"


# Perform sundry cleanup tasks.
reset:
	rm -r coverage
	rm -r apps/static/coverage
	rm .coverage

# Push the repository to GitHub.
mirror:
	git push --force git@github.com:lovett/medley.git master:master
