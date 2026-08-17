.DEFAULT_GOAL := help

MAKEFLAGS += --no-print-directory

SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:

LIB := source make/lib.sh

export REPO_NAME VERBOSE

.PHONY: help setup-hooks

HELP_FILES = make/base.mk $(filter-out make/base.mk,$(MAKEFILE_LIST))

help:
	@printf '\n  \033[1m%s\033[0m\n' "$${REPO_NAME^^}"
	awk 'BEGIN { FS = ":.*?## " } \
	     /^##@/ { printf "\n  \033[2m%s\033[0m\n\n", substr($$0, 5); next } \
	     /^[a-zA-Z][a-zA-Z0-9_-]*:.*?## / { printf "    %-22s%s\n", $$1, $$2 }' $(HELP_FILES)
	printf '\n'

##@ Repositorio

setup-hooks: ## Configurar los git hooks del proyecto
	@$(LIB)
	git config core.hooksPath .githooks
