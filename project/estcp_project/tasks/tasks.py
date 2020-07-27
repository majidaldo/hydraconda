from invoke import task, Collection, call
from estcp_project import root
import yaml
from .. import work
from pathlib import Path

# need a var called ns!!!
ns = coll = collection = Collection()
# PROJECT
coll.add_collection(Collection('project'))
coll.collections['project'].add_collection(Collection('setup'))
coll.collections['project'].add_collection(Collection('action'))
coll.collections['project'].add_collection(Collection('info'))


# WORK DIR
coll.add_collection(Collection('work-dir'))
coll.collections['work-dir'].add_collection(Collection('setup'))
coll.collections['work-dir'].add_collection(Collection('action'))
coll.collections['work-dir'].add_collection(Collection('info'))




@task
def set_dvc_repo(ctx,
                dir=r"\\pnl\projects\ArmyReserve\ESTCP\Machine Learning\software-files\dont-touch\not-code-dvc-repo",
                ):
    """
    Set sharefolder as (non- source code) DVC repository.
    """
    import json
    dir_from_config = (
        ctx.run(f"dvc config --local core.remote sharefolder")
        .stdout
        .strip()
    )
    dir = json.loads(dir_from_config)['url'] if dir_from_config else dir

    dir = Path(dir).resolve().absolute()
    if not dir.is_dir():
        raise FileNotFoundError('not a directory or directory not found')
    
    ctx.run(f"dvc remote add --local sharefolder \"{dir}\" -f")
    sdvc = root / 'data' / 'sample.dvc'
    # will not error if file in (local) cache but wrong remote
    ctx.run(f"dvc pull \"{root/'data'/'sample.dvc'}\"")
coll.collections['project'].collections['setup'].add_task(set_dvc_repo)




@task
def create_project_wrappers(ctx, ):
    """
    Create wrappers around project tool executables.
    """
    #for #dvc, git, invoke, work-on.sh/enter: bash --login -i
    for exe in ['dvc', 'invoke', 'inv',]+['git', 'bash', 'pre-commit']:
        create_exec_wrapper(ctx, exe, work_dir='project')
coll.collections['project'].collections['setup'].add_task(create_project_wrappers)


@task(
    pre=[
        create_project_wrappers,
        call(set_dvc_repo, )],
    default=True)
def setup(ctx,):
     """All setup tasks"""
     pass
coll.collections['project'].collections['setup'].add_task(setup)


def get_current_conda_env():
    import os
    dir = Path(os.getenv('CONDA_PREFIX')) # can't rely conda info active env
    if not dir:
        return
    else:
        return dir.parts[-1]


def _get_current_work_dir():
    import os
    _ = Path(os.curdir).absolute()
    _ = _.relative_to(root)
    if len(_.parts) == 0:
        return
    else:
        if _.parts[0] in (wd.name for wd in work.find_WorkDirs()):
            return _.parts[0]
        else:
            return


@task
def project_root(ctx):
    print(root)
coll.collections['project'].collections['info'].add_task(project_root)



@task
def work_dir_list(ctx):
    """Lists work directories"""
    for wd in work.find_WorkDirs():
        print(wd.name)
coll.collections['project'].collections['info'].add_task(work_dir_list)


@task
def current_work_dir(ctx):
    cd = _get_current_work_dir()
    if cd: print(cd)
    else: exit(1)
coll.collections['work-dir'].collections['info'].add_task(current_work_dir)


def get_current_WorkDir():
    wd = _get_current_work_dir()
    if wd:
        return work.WorkDir(wd)
    return


def _create_WorkDir(ctx, dir):
    """
    Initializes a work dir with special files.
    """
    dir = Path(dir)
    if len(dir.parts) > 1:
        print('keep work directories flat')
    wd = work.WorkDir(dir)
    return wd


cur_work_dir = _get_current_work_dir()
def get_cur_work_dir_help():
    cd = ''
    if cur_work_dir:
        cd += f" Default: {cur_work_dir}"
    return f"Work directory."+cd


@task(help={
    'exe_name': "name of executable",
    'test': "test if executable can be seen before making a wrapper around it"
    })
def create_exec_wrapper(ctx, exe_pth='_stub',  work_dir=cur_work_dir, test=True): #TODO: create script arg?
    """
    Create wrapper around executable in work dir env.
    """
    exe_pth = Path(exe_pth)
    if work_dir not in (wd.name for wd in work.find_WorkDirs()):
        print('work dir not found')
        exit(1)
    wd = work.WorkDir(root / work_dir)
    env_pth = wd.get_env_path()
    if not env_pth:
        raise Exception('no associated environment')

    exe_name = exe_pth.stem

    def create_wrapper(exe_pth, test=True):
        exe_pth = Path(exe_pth)
        exe_name = exe_pth.stem
        exe_prefix_switch = f"-b {exe_pth.parent}" if exe_pth.parent.parts else ''
        from shutil import which
        if not test:
            # overwrites
            ctx.run(f"create-wrappers -t conda {exe_prefix_switch} -f {exe_name} -d {wd.dir/'wbin'} --conda-env-dir {env_pth}")
            return Path(which(exe_name, path=str(wd.dir/'wbin')))  # Path doesn't work until py3.8

        if not exe_pth.parent.parts:
            get_exe_py = f"from shutil import which; print(which(\'{exe_name}\'))"
            exe_pth = ctx.run(f"{wd.dir/'wbin'/'run-in'} python -c \"{get_exe_py}\"", hide='out').stdout.replace('\n', '')
            if exe_pth=='None': raise Exception(f'{exe_name} exe not found')
        else:
            exe_pth = Path(exe_pth).absolute()
            if not exe_pth.exists():
                raise Exception(f'{exe_pth} does not exist')
        return create_wrapper(exe_pth, test=False)

    if exe_name == '_stub':
        return create_wrapper(exe_name, test=False)
    # so now the following doesn't pick up the wrapped exe. breaks out of recursion issues.
    create_wrapper(exe_pth, test=False).unlink()
    wpth = create_wrapper(exe_pth, test=test)
    from shutil import copy2 as copyexe # attempt to copy all metadata (mainly keeping +x attrib)
    from shutil import which
    assert(wpth.stem == exe_name)
    env_exec_pth = wpth.parent / f"{exe_name}-{wd.name}{wpth.suffix}"
    copyexe(wpth, env_exec_pth)
    run_in_pth = which('run-in', path=str(wpth.parent))
    assert(run_in_pth)
    run_in_pth = Path(run_in_pth)
    assert(run_in_pth.exists())
    copyexe(run_in_pth, run_in_pth.parent / f"{run_in_pth.stem}-{wd.name}{run_in_pth.suffix}")
    print(f"created wrapper {wpth} for {exe_name}")
    print(f"created wrapper {env_exec_pth} for {exe_name}")
    return wpth, env_exec_pth
coll.collections['work-dir'].collections['action'].add_task(create_exec_wrapper)


@task
def create_scripts_wrappers(ctx, work_dir=cur_work_dir):
    if work_dir not in (wd.name for wd in work.find_WorkDirs()):
        print('work dir not found')
        exit(1)
    wd = work.WorkDir(root / work_dir)
    sdir = wd.dir / 'scripts'
    assert(sdir.exists())
    (sdir / 'bin').mkdir(exist_ok=True)

    def make_cmd_script(cmds):
        # assuming simple case: just lines of cmds
        if isinstance(cmds, str):
            cmds = [cmds]
        cmds = [cmd.strip() for cmd in cmds]
        lines = []
        al = lambda ln: lines.append(ln)
        #https://stackoverflow.com/questions/17510688/single-script-to-run-in-both-windows-batch-and-linux-bash/17623721#17623721
        al('echo >/dev/null # >nul & GOTO WINDOWS & rem ^')
        # ***********************************************************
        # * NOTE: If you modify this content, be sure to remove carriage returns (\r)
        # *       from the Linux part and leave them in together with the line feeds
        # *       (\n) for the Windows part. In summary:
        # *           New lines in Linux: \n
        # *           New lines in Windows: \r\n
        # ***********************************************************
        # Do Linux Bash commands here... for example:
        #StartDir="$(pwd)"
        # Then, when all Linux commands are complete, end the script with 'exit'...
        al('set -e')
        for i, cmd in enumerate(cmds):
            if not cmd.replace(' ', ''): continue
            if i == 0:
                # pass args to 1st cmd
                al(f"{cmd} \"$@\"")
            else:
                al(cmd)
        al('exit 0')
        al('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
        al(':WINDOWS')
        #'REM Do Windows CMD commands here... for example:
        #SET StartDir=%cd%
        cmds_line = ""
        for i, cmd in enumerate(cmds):
            if not cmd.replace(' ', ''): continue
            if i == 0:
                # pass args to 1st cmd
                cmds_line += f"{cmd} %* &&"
            else:
                cmds_line += f"{cmd} &&"
        al(cmds_line.strip('&&'))
        #REM Then, when all Windows commands are complete... the script is done.
        return tuple(lines)

    def chmod_px(pth):
        import stat
        return pth.chmod(pth.stat().st_mode | stat.S_IEXEC)

    def write_sbin(sbin, lines):
        lines = make_cmd_script(lines)
        lines = [ln.strip()+'\n' for  ln in lines]
        if sbin.suffix == '.sh':
            open(sbin, 'w', newline='\n').writelines(lines)
        else:
            open(sbin, 'w', ).writelines(lines)
        chmod_px(sbin)

    # .r, .sh, .py, .bat., .
    for script_pth in sdir.glob('*'):
        if script_pth.is_dir(): continue
        name = script_pth.stem
        ext = script_pth.suffix[1:] if script_pth.suffix else None
        sbin_bat = sdir / 'bin' / f"{name}.bat"
        sbin_sh =  sdir / 'bin' / f"{name}.sh"
        sbin_cmd =  sdir / 'bin' / f"{name}.cmd"
        sbin_name = sdir / 'bin' / name
        sbins = (sbin_bat, sbin_name) # (win, linux)

        lines = open(script_pth).readlines()
        if ext == 'cmdlines':
            for sbin in sbins: write_sbin(sbin, lines)
            wpths = create_exec_wrapper(ctx, sbin_name,  work_dir=work_dir, test=True)

        elif ext == 'py':
            # prep
            lines = [f"python {script_pth.absolute()}"]
            for sbin in sbins: write_sbin(sbin, lines)
            wpths = create_exec_wrapper(ctx, sbin_name, work_dir=work_dir, test=True)

        elif ext == 'bat':
            wpths = create_exec_wrapper(ctx, script_pth, work_dir=work_dir, test=True)
        elif ext == 'sh':
            from shutil import copy2 as copyexe
            wpths = create_exec_wrapper(ctx, copyexe(script_pth, sbin_name), work_dir=work_dir, test=True)

        else:
            print(f'{script_pth} not processed.')
coll.collections['work-dir'].collections['action'].add_task(create_scripts_wrappers)



@task
def make_devenv(ctx, work_dir=cur_work_dir):
    """
    Create conda development environment.
    """
    assert(work_dir)
    wd = work.WorkDir(work_dir)
    ctx.run(f"conda run --cwd {wd.dir} -n base conda devenv", echo=True) # pyt=True does't work on windows
coll.collections['work-dir'].collections['setup'].add_task(make_devenv)


def _get_setup_names(wd):
    return list(sorted({p.stem for p in (wd.dir/'scripts').glob('setup*') }))

@task(
    help={
        #'setup_list': 'the name of the setup script  (can be used multiple times to list)',
        'prompt': 'prompt setup tasks',
        },
    #iterable = ['setup_list']
)
def run_setup_tasks(ctx, work_dir=cur_work_dir, prompt=False):
    """
    execute setup tasks for the workdir
    """
    # consider ESSS/deps https://github.com/ESSS/conda-devenv/issues/108
    assert(work_dir)
    wd = work.WorkDir(work_dir)
    make_devenv(ctx, work_dir=wd.name)
    import os
    # have to render the devenv first
    dep_work_dirs = ctx.run(f"conda run -n {wd.devenv_name} python -c \"import os; print(os.getenv('RUN_WORK_DIRS'))\"", hide='out').stdout.replace('\n','')
    if dep_work_dirs != 'None':
        dep_work_dirs = [Path(dwd).stem for dwd in dep_work_dirs.split(os.pathsep) if dwd]
    else:
        dep_work_dirs = []
        print('no RUN_WORK_DIRS found!'); exit(1)
    done = []
    for dwd in dep_work_dirs:
        if dwd in done: continue # possibly deduping
        # make the dev env
        if dwd != wd.name:
            if prompt:
                if input(f"create {dwd} env? [enter y] ").lower().strip() == 'y':
                    make_devenv(ctx, work_dir=dwd)
            else:
                make_devenv(ctx, work_dir=dwd)
        create_scripts_wrappers(ctx, work_dir=dwd)
        dWD = work.WorkDir(dwd)
        for asetup in  _get_setup_names(dWD):
            with ctx.cd(str(dWD.dir)):
                if prompt:
                    if input(f"execute {asetup} for {dWD.name}? [enter y] ").lower().strip() == 'y':
                        ctx.run(f"{dWD.dir/'wbin'/'run-in'} {asetup}", echo=True)
                else:
                    ctx.run(    f"{dWD.dir/'wbin'/'run-in'} {asetup}", echo=True)
        done.append(dWD.name)
    #ctx.run(f"conda run --cwd {wd.dir} -n {wd.env name} conda devenv", echo=True) # pyt=True does't work on windows
coll.collections['work-dir'].collections['setup'].add_task(run_setup_tasks)


def _change_dir(wd):
    if wd.dir.resolve() != Path('.').resolve():
        n_up = len(Path('.').absolute().parts) - len(wd.dir.absolute().parts) + 1
        assert( (n_up-1) !=0)
        if n_up>0:
            deeper = True
            rdir = ['..']*n_up + [wd.name]
            rdir = Path(*rdir)
        else:
            deeper = False
            rdir = Path(wd.dir).absolute().relative_to(Path('.').absolute())
        print(f"Change directory to {rdir}.")
        print(f"> cd {rdir}")
        return True
    else:
        return None

# TODO create recreate env task


@task(help={'work_dir': "directory to work in a workdir"})
def work_on(ctx, work_dir, ): # TODO rename work_on_check ?
    """
    Instructs what to do to work on something.
    Keep invoking until desired state achieved.
    """
    cur_branch = ctx.run('git rev-parse --abbrev-ref HEAD', hide='out').stdout.replace('\n','')
    cur_env_name = get_current_conda_env()

    def init_commit(wd):
        ctx.run(f'git add "{wd.dir}"')
        ctx.run(f'git commit -m  " [{wd.name}]  initial placeholder commit"')

    # best programmed with a state diagram. TODO


    # 1. check work dir creation
    wd = work_dir
    if wd not in (wd.name for wd in work.find_WorkDirs()):
        # best to do this from the project env
        # b/c the git hook prepends WORK_DIR
        project_env = work.WorkDir(root/'project').devenv_name  # hardcoding warning
        if cur_env_name !=  project_env:
            print("Change to project environment before creating a new workdir.")
            print(f"> conda activate {project_env}")
            exit(1)
        # state of just creating a workdir
        if cur_branch != 'master':
            if input(f"Current git branch is not 'master'. Enter 'Y' if  you're sure that you want to initialize the work dir in the '{cur_branch}' branch.").lower() == 'y':
                wd = _create_WorkDir(ctx, wd)
                init_commit(wd)
            else:
                print('Switch to master.')
                print('> git checkout master')
                exit(1)
        else:
            wd = _create_WorkDir(ctx, wd)
            init_commit(wd)
    else:
        wd = work.WorkDir(wd)

    # 2. env creation
    minRunenv = \
        wd.minrunenv \
        == yaml.safe_load(open(wd.dir/'environment.run.yml'))
    minDevenv = \
        yaml.safe_load(open(wd.dir/'environment.devenv.yml')) \
        == wd.make_devenv()
    #            'or' instead of 'and' since the intent is to get the user to do /something/.
    if (minRunenv or minDevenv):
        print('Minimal dev or run env detected.')
    make_devenv(ctx, work_dir=wd.name)

    # 4. create wrapper scripts
    for w in (wd.dir / 'wbin').glob('*'): w.unlink()
    create_exec_wrapper(ctx, '_stub', work_dir=wd.name)
    create_scripts_wrappers(ctx, work_dir=wd.name)

    # 5. run setup tasks
    run_setup_tasks(ctx, work_dir=work_dir, )

    # check if devenv in run env includes. TODO

    # 6. check if in env
    if wd.devenv_name != cur_env_name:
        print(f'Activate environment:')
        print(f'> conda activate {wd.devenv_name}')
        exit(1)

    # 7. check if in dir
    if _change_dir(wd):
        exit(1)

    # 8. check if in a branch
    if ('master' == cur_branch) and (wd.name != 'project'):
        print('Notice: You many want to create a branch for your work.')

    print('Ready to work!')
coll.collections['work-dir'].collections['action'].add_task(work_on)
coll.add_task(work_on)


# TODO: recreate is this followed by a workon
@task(help={'work-dir': get_cur_work_dir_help() })
def remove_work_env(ctx, work_dir=cur_work_dir):
    """
    Removes conda environment associated with work dir.
    """
    wd = work_dir
    if wd not in (wd.name for wd in work.find_WorkDirs()):
        print('Work dir not found.')
        exit(1)
    wd = work.WorkDir(wd)
    #                                           sometimes nonzero exit returned :/
    envlist = ctx.run('conda env list', hide='out', warn=True).stdout
    # checking if env created for the workdir
    if envlist.count(wd.devenv_name+'\n') != 1:
        print("No env associated with work dir.")
        exit(0)
    else:
        if wd.devenv_name == get_current_conda_env():
            if wd.devenv_name == 'estcp-project':
                print("Don't remove base/project env.")
            else:
                print("Can't remove current env. Go to another env:")
                print("> conda activate estcp-project")
            exit(1)
        else:
            #(wd.dir / wd.envfn).unlink(missing_ok=True) py3.8
            envfn = (wd.dir / wd.envfn)
            if envfn.exists():
                envfn.unlink()
            print(f"> conda env remove -n {wd.devenv_name}")
coll.collections['work-dir'].collections['action'].add_task(remove_work_env)




#@task TODO
def dvc_run(ctx,  work_dir=cur_work_dir):
    """
    Executes .dvc files.
    """
    ...
    wd = work_dir
    if wd not in (wd.name for wd in work.find_WorkDirs()):
        print('Work dir not found.')
        exit(1)
    wd = work.WorkDir(wd)
    work_on(ctx, wd.dir)
#ns.add_task(dvc_run)

# run dvc conda run
# task: reset/clean env
# clean env
# TODO feature: optionally print out shell cmds.

# ok just do setup.py programmatically

#
coll.collections['project'].add_collection(Collection('_git'))

@task
def prepare_commit_msg_hook(ctx,  COMMIT_MSG_FILE): # could not use work_dir
    """
    (ignore. internal task.) git commit hook for workdir tag
    Uses takes the first dir part to prepend
    """
    import git
    repo = git.Repo(root)
    work_dirs = []
    for pth in repo.index.diff("HEAD"):
        pth = Path(pth.a_path) # a_path or b_path idk
        if len(pth.parts) == 1: # assume project
            work_dirs.append('project')
        else:
            work_dirs.append(pth.parts[0])
    work_dirs = frozenset(work_dirs)
    
    if work_dirs:
        work_dir_tags = ""
        for wd in work_dirs: work_dir_tags += f"[{wd}]"
        message = f"{work_dir_tags} " + open(COMMIT_MSG_FILE, 'r').read()
        cmf = open(COMMIT_MSG_FILE, 'w')
        cmf.write(message)
        cmf.close()
coll.collections['project'].collections['_git'].add_task(prepare_commit_msg_hook)
