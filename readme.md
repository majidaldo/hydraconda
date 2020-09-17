# I. Workflow

This repository represents a 'workspace' for both source code (both 'library' type code and scripts, referred to as just 'code' from here on) _and_ non- source code (data and generated assets, referred to as just 'files' from here on).
In addition, execution environments and workflow tasks are managed as well.

* **Code**, representing fuctionality, configuration, and file _references_ is managed by `git`.
* **Files** are managed by `dvc` ([data science version control](http://dvc.org)).
* **Environments** are managed by [`conda`](https://docs.conda.io) and [`conda devenv`](https://conda-devenv.readthedocs.io).
* **Tasks** are managed by [`invoke`](http://docs.pyinvoke.org).

## Structure

The workflow manages a 'work directory' (workdir) concept: some separated-out unit of work.
It could be a module/library or a one-off experiment.
To keep things as simple as possible, workdirs are the folders directly under the root of the workspace.
The workdir structure is flat so collaborators can immediately identify units of work.
Nonetheless, each workdir can have its own directory hierarchy obviously.

### Development environment file

A [environment.devenv.yml](./project/environment.devenv.template.yml) is in each workdir holding development environment configuration.
The configurtion is specified by environment variables and dependencies.

** 'Internal' Dependencies **
Internal dependencies are other work dirs in the project.
They are specified in the 'includes' section, a directive to include _other_ development environment files.

** 'External' Dependencies **
External dependencies are specified as a list under the 'dependencies' section.
These are 'normal' conda dependency specifications except that some can be excluded from being installed in an environment which includes the environment file in which they are defined.
This is useful to exclude devlopment tools (like test frameworks and code linters) from being installed in an dependent environment.


## Scripts

Script files placed in the 'scripts' directory will be processed to produce wrapped executables.
Currently, .py, .bat, and .sh scripts are supported in addition to a special .cmdlines.
Scripts beginning with 'setup' will be processed and executed as part of an automated setup process.

## Process

The workflow is formalized by the tasks that are defined in the `project` command.
The tasks (try to) align code, files, and execution environments.
The tasks aid the following development process.

0. Activate project environment: `> conda activate estcp-project`.

1. Initialize work directories.

    The `work-on` task (`> project work-on <workdirname>`) is intended to be an entry point into work by automating the following process.

    0. Initialization of

        *Directory contents.*
        A work directory (with environment file) will be created if one does not exist.

        *Environment.*
        A 'default' environment will be created according the the [environment.devenv.yml](./project/environment.devenv.template.yml) template.

    1. Environment check

        Once a workdir has been initialized, the task will instruct to switch to the workdir environment and directory.

2. Manage environment.

    Declare the dependencies by modifying the environment.devenv.yml (in the created directory).
    See conda [devenv documentation](https://conda-devenv.readthedocs.io/en/latest/).

    Invoke `project work-on <workdirname>` from the project environment to make changes to the environment.

3. Manage source and file references.

    Manage (source) code (only) with `git` and keep data and generated assets such as notebooks, intermediate files, documentation, visualizations, and model files out of source control.
    This separation is enforced with a restrictive [.gitignore](.gitignore);
    All files are ignored except patterns that are considered (source) code.

    `dvc run` is useful here to declare an execution consisting of input files, commands, and output files which will generate a .dvc file to be source controlled.
    `dvc add` is useful to just add (and manage) files.
    Use `> dvc pull <dvcfile>` to obtain input files.

    It may be useful to, again, create a branch to represent different versions of the work.

3. Reproduce.

    Reproduction of an execution is achieved when input files, commands, and the execution environment are specified.
    Through a .dvc file, `dvc repro` manages input files and commands (but not the execution environment directly).
    Now, the environment.*.yml files should reflect the development environment.
    So the way to ensure reproduction of the execution is to recreate the development environment as follows:
    1. `> project reset <workdir>`
    2. `> dvc repro <dvcfile>`.

4. Commit source and files.

    The usual `git commit` command has been modified to prepend the commit message with '[workdir]' to help identify top-level work.

    After committing code, representing functionality and an execution process, generated assets should be shared with a `dvc push`.


# II. Development Environment Setup

0. **Obtain source**

    Enter 'base' environment: `> conda activate base`.
    Then obtain source with
    `> git clone https://stash.pnnl.gov/scm/usarml/workspace-code.git workspace`.
    <br>
    The source was cloned into the 'workspace' directory even though it's called 'workspace-code' to emphasize that code and non-code will combine in the directory.

1. **Configure**

    The only required configuration is setting the DVC repository in the project [configuration file](./project/config.yml).
    This repo is on the shared drive at \\\pnl\projects\ArmyReserve\ESTCP\Machine Learning\software-files\dont-touch\not-code-dvc-repo, so check that you can access it.
    Optionally, make this folder available offline for better performance (Windows feature). <br>
    > Do not modify this directory (yourself)!

0. **Bootstrap**

    Executing [bootstrap.sh](./bootstrap.sh) and [bootstrap.bat](./bootstrap.bat) for Mac/Linux and Windows, respectively, will initialize the project.


2. **Check project tools**

    After that, from the 'project' directory, install [project-specific tools](project/environment.run.yml) into a _project_ base environment with:
    `> conda devenv`.

    After entering the project development environment, with `> conda activate estcp-project`, check that you can list development [tasks](project/estcp_project/tasks/tasks.py) with: `> project -l`.
    <br>
    Use `-h` before the task name to learn about the task like:
    ```
    (estcp-project) > project -h project.info.work-dir-list
    Usage: inv[oke] [--core-opts] list-work-dirs [other tasks here ...]

    Docstring:
    Lists work directories

    Options:
    none
    ```


# III. Architecture


The trunk (master branch) contains baseline/common assets (code, data files).
They can be organized as a 'stack' where top layers build on lower layers.


* Layer 0: Workflow tools

    source code mgt.: `git` is the fundamental 'entry point' into the workspace.
    This is closely followed by `dvc` as they work together.


* Layer 1: (Raw) data files

    Mainly MDMS files, EBCS files, and meta data.
    These are stored in /data.

* Layer 2: 'Data interface'

    Metadata database: Structures relationships in the raw data and exposes the relationships as a Python-based object relational map (ORM).

* Layer 3: 'API'

    The API is differentiated from the 'data interface' since it hides 'raw' data connections that are not of interest to an analyst.
    Instead, the API is concerned with presenting a meaningful querying interface to the analyst.

* Layer 4: Analysis

    Examples of analyst-generated assets: visualizations, models, and documents.
    They may be stored as (non- source code) files managed by DVC.

* Layer 5: Applications

    Applications are essentially a manifestation of use cases.
    For example, an user interface could be presented to identify potential equipment faults.

Generally, lower layers are firmer than upper layers.
For example, data are expected to be relatively fixed.
However, the API can change according to need.

This layering can be gleaned by executing `project.info.work-dir-deps-tree`.


<!--
use isse tracker on bitbucket?
-->
