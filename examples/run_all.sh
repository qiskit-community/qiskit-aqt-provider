#!/usr/bin/env bash
# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# Run all Python scripts in the 'examples/' directory.
# Options:
#  -n: dry run
#  -c: collect coverage information
#      Any existing coverage information (.coverage) is wiped.

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
ALL_EXAMPLES=$(find "$SCRIPT_DIR" -name "*.py")

usage() { echo "Usage: $0 [-c|-n]" 1>&2; exit 1; }

while getopts "::cn" option; do
    case "${option}" in
        c)
            coverage=true
            ;;
	n)
	    dry_run=true
	    ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))


coverage="${coverage:-false}"
dry_run="${dry_run:-false}"
cov_opt=""

for example in $ALL_EXAMPLES; do
    echo """Running $(basename "$example")"""
    if "$dry_run"; then
	continue
    fi

    if "$coverage"; then
	coverage run $cov_opt "$example"
    else
	python "$example"
    fi
     cov_opt="-a"  # append all examples to the coverage database
 done
