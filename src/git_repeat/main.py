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

import os
import sys
import argparse
import logging
from .helper import actions

VERSION = '0.1.4'
RECIPE_VERSION = '1.0'


def version_info():
    print(f"git-repeat v{VERSION}\nsupported recipes up to v{RECIPE_VERSION}\n")


def main():
    class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        def __init__(self, prog: str):
            super().__init__(prog, max_help_position=55)

    parser = argparse.ArgumentParser("git-repeat", formatter_class=CustomFormatter,
                                     description="remove repetitive tasks from your development workflow\n\n"
                                                 "for detailed information visit https://github.com/p0intR/git-repeat\n\n"
                                                 "tip: to easily revert changes made by this tool,\n"
                                                 "commit your pending changes on the repository")
    parser.add_argument('-v', '--version', action='store_true', default=False,
                        help='version information')

    subparsers = parser.add_subparsers(title='actions', dest='subparser', help='choose one of these actions')

    # parent parsers
    from_to_parser = argparse.ArgumentParser(add_help=False, formatter_class=CustomFormatter)
    from_to_parser.add_argument('-f', '--from', type=str, default='HEAD~1', dest="rev_from",
                                help='difference calculation from this commit, should have occurred before --to commit')
    from_to_parser.add_argument('-t', '--to', type=str, default='HEAD', dest="rev_to",
                                help='difference calculation to this commit, should have occurred should after --from commit')
    from_to_parser.add_argument('--exclude', type=str, default=r'["logs\\.txt", "Logs\\.txt", "\\.md"]', dest="exclude",
                                help='list of excludes in json format as regex, matching relative file paths are excluded')
    from_to_parser.add_argument('--include', type=str, default='[]', dest="include",
                                help='list of includes in json format as regex, ONLY matching relative file paths are included')

    replacements_parser = argparse.ArgumentParser(add_help=False, formatter_class=CustomFormatter)
    replacements_parser.add_argument('-r', '--replacements', type=str, default="{}",
                                     help='text replacements when repeating commit in json format, for example replacing all '
                                          'foo with bar and all Foo with Bar: {\'foo\':\'bar\',\'Foo\',\'Bar\'}. '
                                          'if this is an array of replacements, the recipe is run multiple times, '
                                          'for example foo with bar and foo with fu: [{\'foo\':\'bar\',\'Foo\',\'Bar\'}, '
                                          '{\'foo\':\'fu\',\'Foo\',\'Fu\'}]. this has the same effect as running git-repeat '
                                          'twice with {\'foo\':\'bar\',\'Foo\',\'Bar\'} and {\'foo\':\'fu\',\'Foo\',\'Fu\'} respectively. '
                                          'if parameter does not start with an { or [ treated as path to json file')
    replacements_parser.add_argument('--dry', action='store_true', default=False, dest="dry_run",
                                     help='dry run, only print changes made but don\'t persist changes or add any files')

    repo_parser = argparse.ArgumentParser(add_help=False, formatter_class=CustomFormatter)
    repo_parser.add_argument('-e', '--encoding', type=str, default='utf-8-sig', dest="encoding",
                             help='encoding used for reading and storing files')
    repo_parser.add_argument('-d', '--debug', action="store_const", default=logging.INFO, const=logging.DEBUG, dest="loglevel",
                             help='enable verbose output')
    repo_parser.add_argument('repo', nargs='?', type=str, default=".",
                             help='path to source code, if using \'run\' or \'recipe\' path must point to a git repository, '
                                  'if using \'apply\' folder structure must match recipe\'s folder structure')

    # run
    parser_run = subparsers.add_parser('run', formatter_class=CustomFormatter, parents=[from_to_parser, replacements_parser, repo_parser],
                                       help='generates recipe on the fly and applies it to repository')

    # recipe
    parser_recipe = subparsers.add_parser('recipe', formatter_class=CustomFormatter, parents=[from_to_parser, repo_parser],
                                          help='generate recipe from repository (to file or stdout)')
    parser_recipe.add_argument('-k', '--keys', type=str, default="[]",
                               help='text replacements keys when applying commit in json format, for example replacing '
                                    'all foo and Foo: [\'foo\', \'Foo\']. if parameter does not start with '
                                    'an [ treated as path to json file')
    parser_recipe.add_argument('-o', '--out', type=str, default="-", dest="out_path", help='output recipe to file, - means stdout')

    # apply
    parser_apply = subparsers.add_parser('apply', formatter_class=CustomFormatter, parents=[replacements_parser, repo_parser],
                                         help='apply recipe to repository (from file or stdin)')
    parser_apply.add_argument('-i', '--in', type=str, default="-", dest="in_path", help='input recipe file to apply, - means stdin')

    args = parser.parse_args()

    def print_help():
        version_info()
        parser.print_help()
        print("\naction: run")
        parser_run.print_help()
        print("\naction: recipe")
        parser_recipe.print_help()
        print("\naction: apply")
        parser_apply.print_help()

    if len(sys.argv) <= 1:
        print_help()
        sys.exit(1)

    if args.version:
        version_info()
        sys.exit(1)

    try:
        # logging
        logger = logging.getLogger("git-repeat")
        formatter = logging.Formatter('%(asctime)s | %(name)s | %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        out_handler = logging.StreamHandler(sys.stdout)
        out_handler.setFormatter(formatter)
        out_handler.addFilter(lambda r: r.levelno < logging.ERROR)
        err_handler = logging.StreamHandler(sys.stderr)
        err_handler.setFormatter(formatter)
        err_handler.addFilter(lambda r: r.levelno >= logging.ERROR)
        logger.addHandler(out_handler)
        logger.addHandler(err_handler)
        logger.setLevel(args.loglevel)

        # actions
        if args.subparser == 'run':
            actions.run(args.rev_from, args.rev_to, args.repo, args.replacements, args.encoding, args.exclude, args.include, args.dry_run, RECIPE_VERSION)

        elif args.subparser == 'recipe':
            actions.recipe(args.rev_from, args.rev_to, args.repo, args.keys, args.out_path, args.encoding, args.exclude, args.include, RECIPE_VERSION)

        elif args.subparser == 'apply':
            actions.apply(args.repo, args.replacements, args.in_path, args.encoding, args.dry_run)

        else:
            print_help()

    except ValueError as ve:
        logger.error(ve)
        sys.exit(1)

    except FileNotFoundError as fe:
        logger.error(fe)
        sys.exit(1)

    except BrokenPipeError as bp:
        logger.debug(bp)
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(1)


if __name__ == '__main__':
    main()
