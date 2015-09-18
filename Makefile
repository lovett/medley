.PHONY: dummy

NOTIFIER := /usr/local/bin/send-notification
PYTHONPATH := $(CURDIR):test

define notify
	$(NOTIFIER) -t "$1" -p 0
endef

test: dummy
	rm .coverage
	rm -rf htmlcov
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/lettercase/main.py apps/lettercase/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/topics/main.py apps/topics/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/headers/main.py apps/headers/test.py
	coverage html

install: dummy
	ansible-playbook ansible/install.yml
	$(call notify,Medley install complete)

update: dummy
	ansible-playbook ansible/update.yml
	$(call notify,Medley update complete)

venv: dummy
	rm -rf venv
	virtualenv --no-site-packages --prompt="♪ ♪ ♪" venv
