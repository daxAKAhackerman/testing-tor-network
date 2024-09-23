SHELL := /usr/bin/env bash

NO_OUT := > /dev/null 2>&1
NO_FAILURE := || true

DOCKER_DIR := docker
CLI_DIR := cli

# If for some reason you don't like 10.5.0.0/16, you can change it here
TOR_SUBNET := 10.5.0.0/16

install:
	@pipenv install
	@cd $(DOCKER_DIR) && docker build -t testing-tor .
	@docker volume create testing-tor $(NO_OUT)
	@docker network create testing-tor --subnet $(TOR_SUBNET) $(NO_OUT) $(NO_FAILURE)

install-dev:
	@pipenv install --dev

lint:
	@pipenv run black --line-length=160 $(CLI_DIR)
	@pipenv run isort --profile=black $(CLI_DIR)
