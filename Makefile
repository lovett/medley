.PHONY: dummy

NOTIFIER := /usr/local/bin/send-notification
PYTHONPATH := $(CURDIR):test

define notify
	$(NOTIFIER) -t "$1" -p 0
endef

test: dummy
	rm -f .coverage
	rm -rf htmlcov
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/lettercase/main.py apps/lettercase/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/topics/main.py apps/topics/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/headers/main.py apps/headers/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/ip/main.py apps/ip/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/whois/main.py apps/whois/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/geodb/main.py apps/geodb/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/registry/main.py apps/registry/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/blacklist/main.py apps/blacklist/test.py
	PYTHONPATH=$(PYTHONPATH) coverage run --branch -a --source apps/awsranges/main.py apps/awsranges/test.py
	coverage html

install: dummy
	ansible-playbook ansible/install.yml
	$(call notify,Medley install complete)

update: dummy
	ansible-playbook ansible/update.yml
	$(call notify,Medley update complete)

venv: dummy
	rm -rf venv
	virtualenv -p python3 --no-site-packages --prompt="♪ ♪ ♪" venv
