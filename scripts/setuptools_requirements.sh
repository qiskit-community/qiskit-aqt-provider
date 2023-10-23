#!/usr/bin/env bash

# Export setuptools-style requirements.txt and requirements-dev.txt
# dependency specifications from the poetry lock file.
# If -c is passed, check instead of overwriting existing targets.

set -eu

usage() { echo "Usage: $0 [-c]" 1>&2; exit 1; }

while getopts "::c" option; do
    case "${option}" in
        c)
            check=true
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

check="${check:-false}"

generate() {
    poetry export --without-hashes --only main --output "$1"
    poetry export --without-hashes --only dev --output "$2"
}

requirements="requirements.txt"
requirements_dev="requirements-dev.txt"

if ${check}; then
    tmp_requirements=$(mktemp)
    tmp_requirements_dev=$(mktemp)

    cleanup() {
	# the shell linter doesn't catch that this code is reachable through the exit trap
	# shellcheck disable=SC2317
	rm -f "${tmp_requirements}"
	# shellcheck disable=SC2317
	rm -f "${tmp_requirements_dev}"
    }

    trap cleanup EXIT

    [[ ! -f "${requirements}" ]] && echo "${requirements} doesn't exist." && exit 1
    [[ ! -f "${requirements_dev}" ]] && echo "${requirements_dev} doesn't exist." && exit 1

    generate "${tmp_requirements}" "${tmp_requirements_dev}"

    # diff exits with status 1 if the inputs differ
    diff -u "${tmp_requirements}" "${requirements}"
    diff -u "${tmp_requirements_dev}" "${requirements_dev}"

    exit 0
fi

generate "${requirements}" "${requirements_dev}"
