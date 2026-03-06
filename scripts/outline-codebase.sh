#!/usr/bin/env bash
set -euo pipefail

{
  tree . -I "_*" -I "*.egg-info" -I __pycache__ -I tests -I build -I ".*" -L 5
} > CODEBASE.txt
