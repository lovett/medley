#!/bin/sh

SCRIPT_DIR=$(dirname "$0")

cd "$SCRIPT_DIR/../.git/hooks"

ln -sf ../hooks/pre-commit
