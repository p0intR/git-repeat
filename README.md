# git-repeat
Remove repetitive tasks from your development workflow by using diffs between git commits to replicate work already done

![XKCD Automation Image](https://imgs.xkcd.com/comics/automation.png) \
[XKCD Automation https://xkcd.com/1319](https://xkcd.com/1319/)

## Motivation
I started a new web project with ASP.NET core. After creating all required entities, 
I was confronted with the tedious task of creating CRUD application services, DTOs, auto-mapping 
configuration, configuration for the site navigation, resource entries for i18n, controllers, view models, 
cshtml pages with tables, create/edit modals, and JavaScript files to make all of that work - and that for each entity.

Why not do it once and automatically repeat all of that for each entity?

The idea is simple: 
* Create all of these things once manually for one of the entities e.g. Entity1 
* Commit these changes
* Get the diff between this and the previous commit
* Replace all occurrences of Entity1 with Entity2 in files and filenames
* Append all changes and add all new files automatically to the repository
* Rinse and repeat for Entity3

All that's left then is updating the automatically generated DTOs and the html tables and create/edit modals. As each entity has 
different fields and since this is requirement specific and everything else is automated I see no inconvenience. With auto-mapping 
and jQuery's serialize() this falls more under customization than implementation at this point.

## How does it work
* Looks at the diff between two commits and processes newly added files and changes made to existing files
* Searches and replaces all replacements supplied inside copies of added files and inside diffs of changed files 
* For changes, the text inside the diff is replaced by replacements and then inserted at the same position
* For newly added files, the file is copied and the target filename is computed by replacements on the source filename
* *Should* work with any language as long as the files are inside a git repository
* Doesn't generate code for you, it is simply copying files and repeating all changes made
* Take care when committing your changes which are later used with git-replace
  * e.g. you may include changes where you reformat a whole file, however this would make the recipe unnecessary large
* git-repeat can be run multiple times with the same recipe
  * Each recipe includes the contents of changed files, therefore untracked changes made to files are taken into account
  * Positions are updated with offsets based on untracked changes made (includes previous runs of git-repeat) - this is done at runtime, the recipe remains unchanged

## Usage
Depending on your installation method git-repeat is available as:
```
user@host:~$ git-repeat 
user@host:~$ python -m git-repeat 
user@host:~/git-repeat/src$ python -m git_repeat.main 
```
Initial help page and supported parameters:
```
git-repeat v0.0.1
supported recipes up to v1.0

usage: git-repeat [-h] [-v] {run,recipe,apply} ...

remove repetitive tasks from your development workflow

for detailed information visit https://github.com/p0intR/git-repeat

tip: to easily revert changes made by this tool,
commit your pending changes on the repository

optional arguments:
  -h, --help          show this help message and exit
  -v, --version       version information (default: False)

actions:
  {run,recipe,apply}  choose one of these actions
    run               generates recipe on the fly and applies it to repository
    recipe            generate recipe from repository (to file or stdout)
    apply             apply recipe to repository (from file or stdin)
```
### Run
Run generates recipe on the fly and applies it to repository:
```
action: run
usage: git-repeat run [-h] [-f REV_FROM] [-t REV_TO] [-r REPLACEMENTS] [-e ENCODING] [-d] [repo]

positional arguments:
  repo                                          path to source code, if using 'run' or 'recipe' path must point to a git repository, if using 'apply' folder structure must match recipe's folder structure (default: .)

optional arguments:
  -h, --help                                    show this help message and exit
  -f REV_FROM, --from REV_FROM                  difference calculation from this commit, should have occurred before --to commit (default: HEAD~1)
  -t REV_TO, --to REV_TO                        difference calculation to this commit, should have occurred should after --from commit (default: HEAD)
  --exclude EXCLUDE                             list of excludes in json format as regex, matching relative file paths are excluded (default: ["logs\\.txt", "Logs\\.txt", "\\.md"])
  --include INCLUDE                             list of includes in json format as regex, ONLY matching relative file paths are included (default: [])
  -r REPLACEMENTS, --replacements REPLACEMENTS  text replacements when repeating commit, for example replacing all foo with bar and all Foo with Bar: {'foo':'bar','Foo','Bar'}. if this is an array of replacements, the recipe is run multiple times, for example foo with bar and foo with fu:
                                                [{'foo':'bar','Foo','Bar'}, {'foo':'fu','Foo','Fu'}]. this has the same effect as running git-repeat twice with {'foo':'bar','Foo','Bar'} and {'foo':'fu','Foo','Fu'} respectively. if parameter does not start with an { or [ treated as path to json file
                                                (default: {})
  --dry                                         dry run, only print changes made but don't persist changes or add any files (default: False)
  -e ENCODING, --encoding ENCODING              encoding used for reading and storing files (default: utf-8-sig)
  -d, --debug                                   enable verbose output (default: 20)
```
### Recipe
Recipe generates recipe from repository:
```
action: recipe
usage: git-repeat recipe [-h] [-f REV_FROM] [-t REV_TO] [-e ENCODING] [-d] [-k KEYS] [-o OUT_PATH] [repo]

positional arguments:
  repo                              path to source code, if using 'run' or 'recipe' path must point to a git repository, if using 'apply' folder structure must match recipe's folder structure (default: .)

optional arguments:
  -h, --help                        show this help message and exit
  -f REV_FROM, --from REV_FROM      difference calculation from this commit, should have occurred before --to commit (default: HEAD~1)
  -t REV_TO, --to REV_TO            difference calculation to this commit, should have occurred should after --from commit (default: HEAD)
  --exclude EXCLUDE                 list of excludes in json format as regex, matching relative file paths are excluded (default: ["logs\\.txt", "Logs\\.txt", "\\.md"])
  --include INCLUDE                 list of includes in json format as regex, ONLY matching relative file paths are included (default: [])
  -e ENCODING, --encoding ENCODING  encoding used for reading and storing files (default: utf-8-sig)
  -d, --debug                       enable verbose output (default: 20)
  -k KEYS, --keys KEYS              text replacements keys when applying commit, for example replacing all foo and Foo: ['foo', 'Foo']. if parameter does not start with an [ treated as path to json file (default: [])
  -o OUT_PATH, --out OUT_PATH       output recipe to file, - means stdout (default: -)
```
### Apply
Apply applies recipe to repository
```
action: apply
usage: git-repeat apply [-h] [-r REPLACEMENTS] [-e ENCODING] [-d] [-i IN_PATH] [repo]

positional arguments:
  repo                                          path to source code, if using 'run' or 'recipe' path must point to a git repository, if using 'apply' folder structure must match recipe's folder structure (default: .)

optional arguments:
  -h, --help                                    show this help message and exit
  -r REPLACEMENTS, --replacements REPLACEMENTS  text replacements when repeating commit, for example replacing all foo with bar and all Foo with Bar: {'foo':'bar','Foo','Bar'}. if this is an array of replacements, the recipe is run multiple times, for example foo with bar and foo with fu:
                                                [{'foo':'bar','Foo','Bar'}, {'foo':'fu','Foo','Fu'}]. this has the same effect as running git-repeat twice with {'foo':'bar','Foo','Bar'} and {'foo':'fu','Foo','Fu'} respectively. if parameter does not start with an { or [ treated as path to json file
                                                (default: {})
  --dry                                         dry run, only print changes made but don't persist changes or add any files (default: False)
  -e ENCODING, --encoding ENCODING              encoding used for reading and storing files (default: utf-8-sig)
  -d, --debug                                   enable verbose output (default: 20)
  -i IN_PATH, --in IN_PATH                      input recipe file to apply, - means stdin (default: -)
```

## Requirements
* Python >= 3.7
* GitPython >= 3.1.27, < 4.0

I have tested git-repeat Python 3.7 and 3.9 and on GitPython 3.1.27.\
Please let me know if there are problems.

## Installation
### Install git-repeat with pip:
```
pip install git-repeat
```

### Install git-repeat from source with setuptools:
Clone the git-repeat repository
```
git clone https://github.com/p0intR/git-repeat
```
Navigate to git-repeat
```
cd git-repeat
```
Build git-repeat and install
```
python setup.py build
python setup.py install
```

### Run without installation:
Clone the git-repeat repository
```
git clone https://github.com/p0intR/git-repeat
```
Navigate to git-repeat src folder
```
cd git-repeat/src
```
Install required packages
```
python -m pip install GitPython>=3.1.27
```
Run git-repeat
```
python -m git_repeat.main
```

## Step-by-step example 
### Create git-repeat recipe
Recipes are used to store diff-information for later use with git-repeat.\
Create a simple recipe from last commit:
```
user@host:~/some-git-repository$ git-repeat recipe -o my-first.recipe .
```
Or create a more complex recipe and remember your replacement keys for later use:
```
user@host:~/some-git-repository$ git-repeat recipe -f HEAD~2 -t HEAD~1 -k "[\"Entity1\", \"entity1\"]" -o my-second.recipe .
```

### Define replacements
Replacements are key->value pairs to replace text inside diffs.
#### Single replacement
```
user@host:~/some-git-repository$ cat my-replacements.json
{
    "Entity1": "Entity2",
    "entity1": "entity2"
}
```
#### Multiple replacements
```
user@host:~/some-git-repository$ cat my-multi-replacements.json
[
    {
        "Entity1": "Entity2",
        "entity1": "entity2"
    },
    {
        "Entity1": "Entity3",
        "entity1": "entity3"
    }
]
```

### Apply git-repeat recipe
Apply applies a recipe with the specified replacements.
```
user@host:~/some-git-repository$ git-repeat apply -r my-replacements.json -i my-first.recipe .
```
If multiple replacements are present in json file, apply is run once for each single replacement.
```
user@host:~/some-git-repository$ git-repeat apply -r my-multi-replacements.json -i my-second.recipe .
```

### Using pipes stdout / stdin
If no input or output is specified, recipe uses stdout and apply uses stdin.
```
user@host:~/some-git-repository$ git-repeat recipe -f HEAD~2 -t HEAD~1 -k "[\"Entity1\", \"entity1\"]" . | git-repeat apply -r my-multi-replacements.json .
```

### Do it all in one line
With run both actions recipe and apply are run in one go without outputting the recipe.
```
user@host:~/some-git-repository$ git-repeat run -r my-replacements.json .
```
```
user@host:~/some-git-repository$ git-repeat run -f HEAD~2 -t HEAD~1 -r my-multi-replacements.json .
```

## Recipe file structure
Recipe files contain all added files, all changes made and the contents of changed files. 

Below you see a modified (removed some details) example for the ASP.NET core web project described in Motivation. This recipe was 
generated by implementing everything for Entity1, committing the changes and then running git-repeat recipe.
```
user@host:~/some-git-repository$ git-repeat recipe
# git-repeat recipe
#
# syntax:
#	# <COMMENT>	comments must start with # and are not treated as such inside |...|
#	VERSION<TAB><VERSION>	file syntax version used, should appear only once at the top
#	KEY<TAB>|<KEY>|	key that can be used for replacements with this recipe, supports multi line
#	COPY<TAB><RELATIVE PATH>	files that are added newly will be copied and texts replaced
#	UPDATE<TAB><RELATIVE PATH>	updates made to files will be replicated with text replacing, followed by lines with <TAB> seperated:
#		<OPERATION><TAB><POSITION><TAB>|<CONTENTS>|
#
#		operation: + or -, if any plus + and minus - share the same line number it will replaced, otherwise it will be inserted at this position
#		position:  eg. 42, these are not line numbers but indices after splitting by whitespaces.. yeah.
#		contents:  text including newlines with the following conditions:
#		           * text must be between |..|
#		           * can be omitted if operation is minus -
#		           * |..| may contain other pipes |
#		           * all whitespaces between |..| are conserved
#
#		here an example:
#		-  42  |// test|
#		+  42  |/*
#			test
#		*/|
#
#		where this could be simplified to:
#		-  42
#		+  42  |/*
#			test
#		*/|
#
#	FILE<TAB><RELATIVE PATH><TAB>|<CONTENTS>|	files that are part of updates are stored alongside this recipe
#	                                         	this allows for tracking of changes made after this recipe was created
#
# feel free to edit this recipe, have fun :)
#
# this file was created at "2022-06-12 12:30:00+0000" from:
# - repository:
#	"/home/user/some-git-repository"
# - from commit: 
#	"Initial commit" by "user" at "2022-06-11 14:00:00+0200"
# - to commit: 
#	"Added Services and UI for Entity1" by "user" at "2022-06-11 15:00:00+0200"
# - files: ([A]dded, [M]odified, [D]eleted, e[X]cluded-by-[E]xclude, e[X]cluded-by-[I]nclude)
#	M XE	src/README.md
#	M XE	src/web/logs/Logs.txt
#	A	src/application/Services/IEntity1AppService.cs
#	A	src/application/Services/Entity1AppService.cs
#	A	src/application/Services/Dto/ListEntity1Dto.cs
#	A	src/application/Services/Dto/Entity1Dto.cs
#	A	src/application/Services/Dto/CreateEntity1Dto.cs
#	A	src/application/Services/Dto/EditEntity1Dto.cs
#	A	src/application/Services/Dto/Entity1Mapper.cs
#	A	src/web/wwwroot/views/Entity1/Index.js
#	A	src/web/wwwroot/views/Entity1/_CreateModal.js
#	A	src/web/wwwroot/views/Entity1/_EditModal.js
#	A	src/web/Controllers/Entity1Controller.cs
#	A	src/web/Models/Entity1/Entity1ListViewModel.cs
#	A	src/web/Models/Entity1/EditEntity1ModalViewModel.cs
#	A	src/web/Views/Entity1/Index.cshtml
#	A	src/web/Views/Entity1/_CreateModal.cshtml
#	A	src/web/Views/Entity1/_EditModal.cshtml
#	M	src/web/Consts/PageNames.cs
#	M	src/core/i18n/en.xml
#	
VERSION	1.0
COPY	src/application/Services/IEntity1AppService.cs
COPY	src/application/Services/Entity1AppService.cs
COPY	src/application/Services/Dto/ListEntity1Dto.cs
COPY	src/application/Services/Dto/Entity1Dto.cs
COPY	src/application/Services/Dto/CreateEntity1Dto.cs
COPY	src/application/Services/Dto/EditEntity1Dto.cs
COPY	src/application/Services/Dto/Entity1Mapper.cs
COPY	src/web/wwwroot/views/Entity1/Index.js
COPY	src/web/wwwroot/views/Entity1/_CreateModal.js
COPY	src/web/wwwroot/views/Entity1/_EditModal.js
COPY	src/web/Controllers/Entity1Controller.cs
COPY	src/web/Models/Entity1/Entity1ListViewModel.cs
COPY	src/web/Models/Entity1/EditEntity1ModalViewModel.cs
COPY	src/web/Views/Entity1/Index.cshtml
COPY	src/web/Views/Entity1/_CreateModal.cshtml
COPY	src/web/Views/Entity1/_EditModal.cshtml
UPDATE	src/web/Consts/PageNames.cs
+	41	|
        public const string Entity1 = "Entity1";|
UPDATE	src/core/i18n/en.xml
+	9	|
		<text name="Entity1">Entity1</text>
		<text name="CreateNewEntity1">Create new entity1</text>
		<text name="EditEntity1">Edit entity1</text>
|
FILE	src/web/PageNames.cs	|namespace Some.Web.Consts
{
    public class PageNames
    {
        public const string Home = "Home";
        public const string Entity1 = "Entity1";
    }
}
|
FILE	src/core/i18n/en.xml	|<?xml version="1.0" encoding="utf-8" ?>
<texts>
		<text name="Entity1">Entity1</text>
		<text name="CreateNewEntity1">Create new entity1</text>
		<text name="EditEntity1">Edit entity1</text>

		<text name="HomePage" value="Home page" />
</texts>
|
```

## License
git-repeat is licensed under the GPLv3. See LICENSE.md

## Repository
You find the [git repository](https://github.com/p0intR/git-repeat) at GitHub.
