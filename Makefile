SHELL := /usr/bin/env bash
DOCKER_DIR := docker
NO_OUT := > /dev/null 2>&1

install:
	@pipenv install
	@cd $(DOCKER_DIR) && docker build -t home-tor .
	@docker volume create home-tor $(NO_OUT)
	@docker network create home-tor --subnet 10.5.5.0/24 $(NO_OUT) || true

install-dev:
	@pipenv install --dev

lint:
	@pipenv run black --line-length=160 cli/
	@pipenv run isort --profile=black cli/
