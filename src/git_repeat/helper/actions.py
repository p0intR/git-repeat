# This file is part of git-repeat.
#
# git-repeat is free software: you can redistribute it and/or modify it under the terms
# of the GNU General Public License as published by the Free Software Foundation,
# either version 3 of the License, or (at your option) any later version.
#
# git-repeat is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with git-repeat.
# If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import sys
import json
import logging
from git import Repo, Commit
from git.exc import InvalidGitRepositoryError
from .differences import update_repository, diff_to_data, data_check_files_exist, data_to_recipe, recipe_to_data


def _get_git_repo(repo_path, rev_from, rev_to) -> (Repo, Commit, Commit):
    try:
        repo = Repo(repo_path)
        commits = list(repo.iter_commits(rev_to))
        count = len(commits)

        if count < 2:
            raise ValueError(f"At least two commits must be present in repository since \"{rev_to}\".")

        commit_to = repo.commit(rev_to)
        commit_from = repo.commit(rev_from)

        if commit_to.committed_datetime < commit_from.committed_datetime:
            raise ValueError(f"Commit \"{rev_to}\" must be after \"{rev_from}\".")

        return repo, commit_from, commit_to

    except InvalidGitRepositoryError:
        raise ValueError(f"Folder at \"{repo_path}\" must be a git repository.")


def run(rev_from, rev_to, repo_path, replacements, encoding, exclude, include, dry_run, version):
    if dry_run:
        logging.getLogger("git-repeat").info(f"Dry-run enabled")

    if replacements[0] != "{":
        with open(replacements, mode='r') as kf:
            replacements = kf.read()

    repo, commit_from, commit_to = _get_git_repo(repo_path, rev_from, rev_to)
    replacements = json.loads(replacements)
    exclude = json.loads(exclude)
    include = json.loads(include)

    diffs = commit_from.diff(commit_to)
    data = diff_to_data(diffs, replacements.keys(), encoding, exclude, include, version)

    if isinstance(replacements, list):
        logging.getLogger("git-repeat").info(f"Multiple replacements provided")

        counter = 1
        for r in replacements:
            logging.getLogger("git-repeat").info(f"Run #{counter}")
            update_repository(repo.working_dir, encoding, dry_run, r, data)
            counter += 1
    else:
        update_repository(repo.working_dir, encoding, dry_run, replacements, data)


def recipe(rev_from, rev_to, repo_path, keys, out_path, encoding, exclude, include, version):
    if keys[0] != "[":
        with open(keys, mode='r') as kf:
            keys = kf.read()

    repo, commit_from, commit_to = _get_git_repo(repo_path, rev_from, rev_to)
    keys = json.loads(keys)
    exclude = json.loads(exclude)
    include = json.loads(include)

    diffs = commit_from.diff(commit_to)

    data = diff_to_data(diffs, keys, encoding, exclude, include, version)
    output = data_to_recipe(repo, commit_from, commit_to, diffs, exclude, include, data)

    if out_path == '-':
        print(output, end='')
    else:
        with open(out_path, mode="w", encoding=encoding) as of:
            of.write(output)


def apply(repo_path, replacements, in_path, encoding, dry_run):
    if dry_run:
        logging.getLogger("git-repeat").info(f"Dry-run enabled")

    if replacements[0] != "{":
        with open(replacements, mode='r') as kf:
            replacements = kf.read()

    replacements = json.loads(replacements)

    recipe_str = ""
    if in_path == '-':
        for line in sys.stdin:
            recipe_str += line
    else:
        with open(in_path, mode='r', encoding=encoding) as ir:
            recipe_str = ir.read()

    data = recipe_to_data(recipe_str)
    data_check_files_exist(repo_path, data)

    if isinstance(replacements, list):
        logging.getLogger("git-repeat").info(f"Multiple replacements provided")

        counter = 1
        for r in replacements:
            logging.getLogger("git-repeat").info(f"Run #{counter}")
            _check_keys_replacements(data['keys'], r)
            update_repository(repo_path, encoding, dry_run, r, data)
            counter += 1
    else:
        _check_keys_replacements(data['keys'], replacements)
        update_repository(repo_path, encoding, dry_run, replacements, data)


def _check_keys_replacements(keys, replacements):
    for key in keys:
        if key not in replacements:
            logging.getLogger("git-repeat").warning(f"Recipe key \"{key}\" not in replacements")

    for key in replacements:
        if key not in keys:
            logging.getLogger("git-repeat").warning(f"Replacement \"{key}\" not in recipe keys")

    for key in replacements:
        logging.getLogger("git-repeat").info(f"Replacing \"{key}\" with \"{replacements[key]}\"")
