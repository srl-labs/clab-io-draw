#!/usr/bin/env bash
# Copyright 2023 Nokia
# Licensed under the BSD 3-Clause License.
# SPDX-License-Identifier: BSD-3-Clause


set -o errexit
set -o pipefail


# testing release-triggered workflow
function test-on-push {
  gh act release -W '.github/workflows/cicd.yml' -e .github/workflows/release-event.json -s GITHUB_TOKEN="$(gh auth token)" --matrix platform:linux/amd64
}

function test-on-release {
  gh act release -W '.github/workflows/cicd.yml' -e .github/workflows/release-event.json -s GITHUB_TOKEN="$(gh auth token)" --matrix platform:linux/amd64
}

# -----------------------------------------------------------------------------
# Bash runner functions.
# -----------------------------------------------------------------------------
function help {
  printf "%s <task> [args]\n\nTasks:\n" "${0}"

  compgen -A function | grep -v "^_" | cat -n

  printf "\nExtended help:\n  Each task has comments for general usage\n"
}

"${@:-help}"