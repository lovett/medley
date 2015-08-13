.PHONY: dummy

NOTIFIER := /usr/local/bin/send-notification
PYTHONPATH := $(CURDIR)

define notify
	$(NOTIFIER) -t "$1" -p 0
endef

test: dummy
	PYTHONPATH=$(PYTHONPATH) py.test test/test_server.py

install: dummy
	ansible-playbook ansible/install.yml
	$(call notify,Medley install complete)

update: dummy
	ansible-playbook ansible/update.yml
	$(call notify,Medley update complete)

venv: dummy
	rm -rf venv
	virtualenv --no-site-packages --prompt="♪ ♪ ♪" venv
