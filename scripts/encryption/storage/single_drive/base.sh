#!/bin/bash
# shellcheck disable=SC1090  # Can't follow non-constant source. Use a directive to specify location.
source "$(dirname "$(readlink -f "${0}")")/../base.sh" || (echo "Loading base.sh failed." && exit 1)
