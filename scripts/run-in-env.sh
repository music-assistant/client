#!/usr/bin/env sh
set -eu

# Activate pyenv and virtualenv if present, then run the specified command

# pyenv, pyenv-virtualenv
if [ -s .python-version ]; then
    PYENV_VERSION=$(head -n 1 .python-version)
    export PYENV_VERSION
fi

# other common virtualenvs
my_path=$(git rev-parse --show-toplevel)

# A git worktree usually has no virtualenv of its own, so search the main checkout as well.
# A worktree's git dir differs from the common git dir, which lives in the main checkout.
git_dir=$(git rev-parse --path-format=absolute --git-dir 2>/dev/null || true)
common_dir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
main_root=""
if [ -n "$common_dir" ] && [ "$git_dir" != "$common_dir" ]; then
  main_root=$(dirname "$common_dir")
fi

for root in "$my_path" ${main_root:+"$main_root"}; do
  for venv in venv .venv .; do
    if [ -f "${root}/${venv}/bin/activate" ]; then
      . "${root}/${venv}/bin/activate"
      break 2
    fi
  done
done

exec "$@"
