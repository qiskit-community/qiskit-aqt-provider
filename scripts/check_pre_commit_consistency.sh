#!/usr/bin/env bash

# (C) Copyright Alpine Quantum Technologies GmbH 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

# Check consistency between versions of the pre-commit hooks
# and the packages installed by poetry.

set -euo pipefail

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Retrieve the version of a Python package installed by Poetry.
installed_package_version() {
    package_name="$1"
    # FIXME: install poetry-export plugin to not need to silence the warning here.
    package_version=$(poetry export \
           --only dev \
	   --format requirements.txt \
	   --without-hashes \
	   --without-urls 2> /dev/null | \
	   sed -nr "s/$package_name==([0-9][0-9.]*).*/\1/p")
    echo "$package_version"
}

# Retrieve the version of a pre-commit hook.
pre_commit_hook_version() {
    tool_name="$1"
    config_path="$SCRIPT_DIR/../.pre-commit-config.yaml"
    hook_version=$(yq -r ".repos[] | select(.repo | test(\"$tool_name\")).rev" "$config_path")
    hook_version=${hook_version#v}
    echo "$hook_version"
}

tools=(ruff typos pyproject-fmt interrogate)
exit_code=0

for tool in "${tools[@]}"; do
    package=$(installed_package_version "$tool")
    hook=$(pre_commit_hook_version "$tool")
    echo -n "$tool: package=$package hook=$hook "
    if [ -n "$package" ] && [ -n "$hook" ] && [ "$package" = "$hook" ]; then
	echo " OK"
    else
	echo " FAIL"
	exit_code=1
    fi
done

exit "$exit_code"
