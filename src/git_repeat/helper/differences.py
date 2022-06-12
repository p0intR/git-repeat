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

import os
import re
import logging
import difflib
from datetime import datetime
from git import Repo, Commit, Diff, DiffIndex


# -------------------------
# Git diff to internal data structure
# -------------------------
def _untracked_offset(current, untracked):
    offsets = {}

    i, j, offset = 0, 0, 0
    for s in difflib.ndiff(current, untracked):
        # print(f'Untracked offset: {offset} {i} {s[:1]} "{s[2:]}"')
        if s[0] == ' ':
            offsets[i] = offset
            i += 1
        elif s[0] == '-':
            offset -= 1
            offsets[i] = offset
        elif s[0] == '+':
            offset += 1
            offsets[i] = offset

    return offsets


def _get_difference(current, previous):
    inserts = []
    removals = []

    index, text = 0, ""
    i, j = 0, -1
    for s in difflib.ndiff(previous, current):
        # print(f'Difference: {index} {i} {s[:1]} "{s[2:]}"')
        if s[0] == ' ':
            # ignore same as before
            i += 1
        elif s[0] == '-':
            # ignore deleted line
            if len(text) > 0:
                inserts.append((index, text))
            text = ""
            index = 0
            removals.append(i)
            j = -1
        elif s[0] == '+':
            # processes changed line
            if j == i - 1:
                text += s[2:]
            else:
                if len(text) > 0:
                    inserts.append((index, text))
                text = s[2:]
                index = i

            j = i
            i += 1

    if len(text) > 0:
        inserts.append((index, text))

    return inserts, removals


def _check_path(patterns: list[str], path:str):
    for pattern in patterns:
        if re.search(pattern, path):
            return True
    return False


def diff_to_data(diffs: DiffIndex, keys: list[str], encoding: str, exclude: list[str], include: list[str], version: str):
    data = {
        'version': version,
        'keys': keys,
        'changes': {},
        'copies': []
    }

    for diff in diffs:
        if len(exclude) > 0 and _check_path(exclude, diff.a_path):
            continue
        if len(include) > 0 and not _check_path(include, diff.a_path):
            continue

        if diff.new_file:
            data['copies'].append(diff.a_path)

        elif diff.deleted_file:
            continue

        elif diff.renamed_file:
            continue

        else:
            previous_text = diff.a_blob.data_stream.read().decode(encoding)
            current_text = diff.b_blob.data_stream.read().decode(encoding)

            previous = re.split(r'(\s+)', previous_text)
            current = re.split(r'(\s+)', current_text)

            inserts, removals = _get_difference(current, previous)

            if len(inserts) < 1:
                continue

            data['changes'][diff.a_path] = {
                'inserts': inserts,
                'removals': removals,
                'file': current_text
            }

    return data


def data_check_files_exist(repo_path: str, data):
    errors = []

    for copy in data['copies']:
        if not os.path.exists(os.path.join(repo_path, copy)):
            errors.append(f"COPY file \"{copy}\" does not exist")

    for update in data['changes']:
        if len(data['changes'][update]['inserts']) < 1:
            continue

        if not os.path.exists(os.path.join(repo_path, update)):
            errors.append(f"UPDATE file \"{update}\" does not exist")

    if len(errors) > 0:
        raise ValueError(f"File(s) required by this recipe do(es) not exist in repo \"{repo_path}\":\n" + "\n".join(errors))


# -------------------------
# Handle copies and updates
# -------------------------
def update_repository(repo_path: str, encoding: str, dry_run: bool, replacements, data):
    for copy in data['copies']:
        logging.getLogger("git-repeat").info(f"Copying file {copy}")
        _process_new(repo_path, copy, encoding, dry_run, replacements)

    for change in data['changes']:
        logging.getLogger("git-repeat").info(f"Updating file {change}")
        _process_change(repo_path, change, encoding, dry_run, data['changes'][change], replacements)


def _process_change(repo_path: str, file: str, encoding: str, dry_run: bool, changes, replacements):
    file_path = os.path.join(repo_path, file)
    with open(file_path, mode="r", encoding=encoding) as f:
        contents = f.read()
        contents = re.split(r'(\s+)', contents)

    untracked = _untracked_offset(re.split(r'(\s+)', changes['file']), contents) if changes['file'] is not None else []
    inserts, removals = changes['inserts'], changes['removals']

    if len(inserts) < 1:
        return

    offset = 0
    for b in inserts:
        text = b[1]
        for search, replace in replacements.items():
            text = text.replace(search, replace)

        untracked_offset = 0
        if b[0] in untracked:
            untracked_offset = untracked[b[0]]

        if b[0] in removals:
            contents[b[0] + offset + untracked_offset] = text
        else:
            contents.insert(b[0] + offset + untracked_offset, text)
            offset += 1

        info = text.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
        logging.getLogger("git-repeat").debug(f'Updated at line {b[0]} (+offset {offset + untracked_offset}) with "{info}"')

    if dry_run:
        return

    with open(file_path, mode='w', encoding=encoding) as f:
        f.write(''.join(contents))
        f.flush()


def _process_new(repo_path: str, copy: str, encoding: str, dry_run: bool, replacements):
    template_rel_path = copy
    new_rel_path = template_rel_path
    for search, replace in replacements.items():
        new_rel_path = new_rel_path.replace(search, replace)

    template_path = os.path.join(repo_path, template_rel_path)
    new_path = os.path.join(repo_path, new_rel_path)

    with open(template_path, mode="r", encoding=encoding) as f:
        contents = f.read()

    if len(contents) < 1:
        logging.getLogger("git-repeat").debug(f"Empty file, skipping.")
        return

    for search, replace in replacements.items():
        contents = contents.replace(search, replace)

    logging.getLogger("git-repeat").debug(f"New file {new_rel_path}")

    if dry_run:
        return

    os.makedirs(os.path.dirname(new_path), exist_ok=True)
    with open(new_path, mode="w", encoding=encoding) as f:
        f.write(contents)
        f.flush()


# -------------------------
# Recipe IO
# -------------------------
def data_to_recipe(repo: Repo, commit_from: Commit, commit_to: Commit, diffs: DiffIndex, exclude: list[str], include: list[str], data) -> str:
    output = "# git-repeat recipe\n"
    output += "#\n"
    output += "# syntax:\n"
    output += "#\t# <COMMENT>\tcomments must start with # and are not treated as such inside |...|\n"
    output += "#\tVERSION<TAB><VERSION>\tfile syntax version used, should appear only once at the top\n"
    output += "#\tKEY<TAB>|<KEY>|\tkey that can be used for replacements with this recipe, supports multi line\n"
    output += "#\tCOPY<TAB><RELATIVE PATH>\tfiles that are added newly will be copied and texts replaced\n"
    output += "#\tUPDATE<TAB><RELATIVE PATH>\tupdates made to files will be replicated with text replacing, followed by lines with <TAB> seperated:\n"
    output += "#\t\t<OPERATION><TAB><POSITION><TAB>|<CONTENTS>|\n"
    output += "#\n"
    output += "#\t\toperation: + or -, if any plus + and minus - share the same line number it will replaced, otherwise it will be inserted at this position\n"
    output += "#\t\tposition:  eg. 42, these are not line numbers but indices after splitting by whitespaces.. yeah.\n"
    output += "#\t\tcontents:  text including newlines with the following conditions:\n"
    output += "#\t\t           * text must be between |..|\n"
    output += "#\t\t           * can be omitted if operation is minus -\n"
    output += "#\t\t           * |..| may contain other pipes |\n"
    output += "#\t\t           * all whitespaces between |..| are conserved\n"
    output += "#\n"
    output += "#\t\there an example:\n"
    output += "#\t\t-  42  |// test|\n"
    output += "#\t\t+  42  |/*\n#\t\t\ttest\n#\t\t*/|\n"
    output += "#\n"
    output += "#\t\twhere this could be simplified to:\n"
    output += "#\t\t-  42\n"
    output += "#\t\t+  42  |/*\n#\t\t\ttest\n#\t\t*/|\n"
    output += "#\n"
    output += "#\tFILE<TAB><RELATIVE PATH><TAB>|<CONTENTS>|\tfiles that are part of updates are stored alongside this recipe\n"
    output += "#\t                                         \tthis allows for tracking of changes made after this recipe was created\n"
    output += "#\n"
    output += "# feel free to edit this recipe, have fun :)\n"
    output += "#\n"
    output += f'# this file was created at \"{datetime.utcnow():%Y-%m-%d %H:%M:%S+0000}\" from:\n'
    output += "# - repository:\n"
    output += f'#\t"{repo.working_dir}"\n'
    output += "# - from commit: \n"
    output += f'#\t"{commit_from.summary}" by "{commit_from.author}" at "{commit_from.committed_datetime:%Y-%m-%d %H:%M:%S%z}"\n'
    output += "# - to commit: \n"
    output += f'#\t"{commit_to.summary}" by "{commit_to.author}" at "{commit_to.committed_datetime:%Y-%m-%d %H:%M:%S%z}"\n'
    output += "# - files: ([A]dded, [M]odified, [R]enamed, [D]eleted, e[X]cluded-by-[E]xclude, e[X]cluded-by-[I]nclude)\n"

    for diff in diffs:
        info = ""
        if len(exclude) > 0 and _check_path(exclude, diff.a_path):
            info = " XE"
        if len(include) > 0 and not _check_path(include, diff.a_path):
            info = " XI"

        if diff.new_file:
            output += f"#\tA{info}\t{diff.a_path}\n"
        elif diff.deleted_file:
            output += f"#\tD{info}\t{diff.a_path}\n"
        elif diff.renamed_file:
            output += f"#\tR{info}\t{diff.a_path}\n"
        else:
            output += f"#\tM{info}\t{diff.a_path}\n"

    output += "#\n"
    output += f"VERSION\t{data['version']}\n"

    for key in data['keys']:
        output += f"KEY\t|{key}|\n"

    for copy in data['copies']:
        output += f"COPY\t{copy}\n"

    for update in data['changes']:
        if len(data['changes'][update]['inserts']) < 1:
            continue

        output += f"UPDATE\t{update}\n"
        for b in data['changes'][update]['inserts']:
            if b[0] in data['changes'][update]['removals']:
                output += f"-\t{b[0]}\n"

            output += f"+\t{b[0]}\t|{b[1]}|\n"

    for update in data['changes']:
        if len(data['changes'][update]['inserts']) < 1:
            continue

        output += f"FILE\t{update}\t|{data['changes'][update]['file']}|\n"

    return output


def _add_block(data, block_file, block_type, block_index, block, offset=-2):
    if block_type == 'keys':
        data['keys'].append(block[:offset])
    elif block_type in ['inserts', 'removals', 'file']:
        if block_file not in data['changes']:
            data['changes'][block_file] = {
                'inserts': [],
                'removals': [],
                'file': None
            }

        if block_type == 'inserts':
            data['changes'][block_file]['inserts'].append((block_index, block[:offset]))
        elif block_type == 'removals':
            data['changes'][block_file]['removals'].append(block_index)
        elif block_type == 'file':
            data['changes'][block_file]['file'] = block


def _handle_command(i, elements, data, block_file):  # -> block_file, block_type, block_index, block
    if elements[0] == "VERSION":
        if len(data['version']) > 0:
            logging.getLogger("git-repeat").warning("Recipe line {i}, VERSION should only appear once")
        else:
            data['version'] = elements[1].strip()

        return None, None, -1, ""

    if elements[0] == "KEY":
        if len(elements) < 2 or len(elements[1]) < 1 or elements[1][0] != '|':
            raise ValueError(f"Recipe line {i}, KEY expects a key |..|")

        return None, "keys", -1, elements[1][1:]

    elif elements[0] == "COPY":
        data['copies'].append(elements[1].strip())
        return None, None, -1, ""

    elif elements[0] == "UPDATE":
        return elements[1].strip(), None, -1, ""

    elif elements[0] == "+":
        if len(elements) < 3 or len(elements[2]) < 1 or elements[2][0] != '|':
            raise ValueError(f"Recipe line {i}, + expects contents |..|")

        if block_file is None or len(block_file) < 1:
            raise ValueError(f"Recipe line {i}, + expects previous UPDATE statement with relative file path")

        return block_file, "inserts", int(elements[1]), elements[2][1:]

    elif elements[0] == "-":
        if block_file is None or len(block_file) < 1:
            raise ValueError(f"Recipe line {i}, - expects previous UPDATE statement with relative file path")

        if len(elements) > 2 and elements[2][0] == '|':
            return block_file, "removals", int(elements[1]), elements[2][1:]
        else:
            _add_block(data, block_file, "removals", int(elements[1]), "")
            return block_file, None, -1, ""

    elif elements[0] == "FILE":
        if len(elements) < 3 or len(elements[2]) < 1 or elements[2][0] != '|':
            raise ValueError(f"Recipe line {i}, FILE expects contents |..|")

        return elements[1].strip(), "file", -1, elements[2][1:]


def recipe_to_data(recipe):
    data = {
        'version': "",
        'keys': [],
        'changes': {},
        'copies': []
    }

    commands = ["VERSION", "KEY", "COPY", "UPDATE", "+", "-", "FILE"]
    lines = recipe.splitlines(keepends=True)
    block_file = None
    block_type = None
    block_index = -1
    block = ""

    for i, line in enumerate(lines):
        if len(line) < 1:
            continue

        if line[0] == '#' and block_type is None:
            continue

        elements = line.split("\t")
        if len(elements) < 1:
            continue

        # if this line is a valid command
        if elements[0] in commands:
            if block_type is not None:
                # check if last block has ended with a pipe or is an empty block
                if len(block) >= 2 and block[-2:] == "|\n":
                    _add_block(data, block_file, block_type, block_index, block)
                    block_file, block_type, block_index, block = _handle_command(i, elements, data, block_file)
                # else we continue on, command is likely part of block
                else:
                    block += line
            else:
                block_file, block_type, block_index, block = _handle_command(i, elements, data, block_file)

        elif block_type is not None:
            block += line
        else:
            if len(line.strip()) == 0:
                logging.getLogger("git-repeat").debug(f"Recipe does contain empy line at {i}")
            else:
                raise ValueError(f"Malformed recipe at line {i}, command {elements[0]} not understood.")

    if block_type is not None:
        # check if there is a pipe in the end, if so the block can be added
        check = block.rstrip("\n ")
        if (
            len(check) >= 1 and check[-1] == "|"
        ):
            # reduce length of block until |
            _add_block(data, block_file, block_type, block_index, block[:block.rfind("|")], 0)
        else:
            raise ValueError(f"Malformed recipe at EOF with open block: |{block}\n\nNot sure if this is the whole contents of file.\nAre you missing a pipe | ?")

    if len(data['version']) < 1:
        logging.getLogger("git-repeat").warning("Recipe does not contain VERSION information")

    for update in data['changes']:
        if len(data['changes'][update]['inserts']) < 1:
            continue

        if data['changes'][update]['file'] is None:
            logging.getLogger("git-repeat").warning(f"Recipe is missing corresponding FILE contents for UPDATE file \"{update}\"")

    return data
