# SPDX-License-Identifier: GPL-3.0-or-later
PREFIX ?= /usr/local
DESTDIR ?=
PYTHON ?= python3

.PHONY: all check test lint install uninstall dist

all: check

check:
	sh -n horodater.sh
	$(PYTHON) -B -m unittest discover -s tests -v

test: check

lint:
	shellcheck -s sh horodater.sh

install:
	install -d "$(DESTDIR)$(PREFIX)/bin"
	install -m 755 horodater.sh "$(DESTDIR)$(PREFIX)/bin/horodater"

uninstall:
	rm -f "$(DESTDIR)$(PREFIX)/bin/horodater"

dist:
	$(PYTHON) -B tools/dist.py
