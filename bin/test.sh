#!/usr/bin/env bash
##
# Run tests in CI.
#
set -e

echo "==> Lint code"
ahoy lint

echo "==> Run Unit tests"
ahoy test-unit

echo "==> Run BDD tests"
ahoy install-site
ahoy cli "rm -r test/screenshots || true"
ahoy test-bdd || (ahoy logs; exit 1)
