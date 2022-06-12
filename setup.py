import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="git-repeat",
    version="0.1.0",
    author="p0intR",
    description="Remove repetitive tasks from your development workflow by using git diffs to replicate work already done",
    license="GPLv3",
    url="https://github.com/p0intR/git-repeat",
    project_urls={
        "Source": "https://github.com/p0intR/git-repeat",
    },
    long_description=long_description,
    long_description_content_type='text/markdown',
    package_dir={
        "": "src",
        "git_repeat": "src/git_repeat",
        "git_repeat.helper": "src/git_repeat/helper"
    },
    packages=['git_repeat', 'git_repeat.helper'],
    install_requires=[
        "gitpython>=3.1.27,<4"
    ],
    keywords=["git-repeat", "python"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    entry_points={
        "console_scripts": ["git-repeat=git_repeat.main:main"]
    },
    zip_safe=False,
    python_requires='>=3.7',
)
