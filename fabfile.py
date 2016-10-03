#
#    ICRAR - International Centre for Radio Astronomy Research
#    (c) UWA - The University of Western Australia, 2016
#    Copyright by UWA (in the framework of the ICRAR)
#    All rights reserved
#
#    This library is free software; you can redistribute it and/or
#    modify it under the terms of the GNU Lesser General Public
#    License as published by the Free Software Foundation; either
#    version 2.1 of the License, or (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#    Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public
#    License along with this library; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston,
#    MA 02111-1307  USA
#

"""
Fabric file for building installing and testing Python projects

Authors: A Wicenec and D Pallot

ICRAR 2015
"""
import os

from fabric.api import run, put, env, local
from fabric.context_managers import cd
from fabric.contrib.files import append, exists
from fabric.decorators import task


APP_PYTHON_VERSION = '2.7'
APP_PYTHON_URL = 'https://www.python.org/ftp/python/2.7.8/Python-2.7.8.tgz'
VIRTUALENV_URL = 'https://pypi.python.org/packages/source/v/virtualenv/virtualenv-12.0.7.tar.gz'


VENV_DIR = 'projects' # virtual env directory relative to current user home
PROJECT = 'dfms' # project name

class FabricException(Exception): pass
env.abort_exception = FabricException



def set_env():
    env.HOME = run("echo ~")
    env.APP_DIR_ABS = "{0}/{1}/{2}".format(env.HOME, VENV_DIR, PROJECT)


def to_boolean(choice, default=False):
    """Convert the yes/no to true/false

        :param choice: the text string input
        :type choice: string
        """
    valid = {"yes":True,   "y":True,  "ye":True,
        "no":False,     "n":False}
    choice_lower = choice.lower()
    if choice_lower in valid:
        return valid[choice_lower]
    return default


def check_command(command):
    """
        Check existence of command remotely

        INPUT:
        command:  string

        OUTPUT:
        Boolean
        """
    res = run('if command -v {0} &> /dev/null ;then command -v {0};else echo ;fi'.format(command))
    return res


def check_dir(directory):
    """
        Check existence of remote directory
        """
    res = run('if [ -d {0} ]; then echo 1; else echo ; fi'.format(directory))
    return res


def check_python():
    """
        Check for the existence of correct version of python

        INPUT:
        None

        OUTPUT:
        path to python binary    string, could be empty string
        """
    # Try whether there is already a local python installation for this user
    ppath = os.path.realpath(env.APP_DIR_ABS+'/../python')
    ppath = check_command('{0}/bin/python{1}'.format(ppath, APP_PYTHON_VERSION))
    if ppath:
        return ppath
    # Try python2.7 first
    ppath = check_command('python{0}'.format(APP_PYTHON_VERSION))
    if ppath:
        env.PYTHON = ppath
        return ppath


def virtualenv(command):
    """
        Just a helper function to execute commands in the virtualenv
        """

    env.activate = 'source {0}/bin/activate'.format(env.APP_DIR_ABS)
    with cd(env.APP_DIR_ABS):
        run(env.activate + ' && ' + command)

def virtualenv_nocd(command):
    """
    A helper function to execute commands in the virtualenv without
    changing the current working directory
    """
    run('source "{0}/bin/activate" && {1}'.format(env.APP_DIR_ABS, command))


@task
def python_setup():
    """
        Ensure that there is the right version of python available
        If not install it from scratch in user directory.

        INPUT:
        None

        OUTPUT:
        None
        """
    set_env()

    with cd('/tmp'):
        run('wget --no-check-certificate -q {0}'.format(APP_PYTHON_URL))
        base = os.path.basename(APP_PYTHON_URL)
        pdir = os.path.splitext(base)[0]
        run('tar -xzf {0}'.format(base))
    ppath = run('echo $PWD') + '/python'
    with cd('/tmp/{0}'.format(pdir)):
        #run('./configure --prefix {0};make;make install'.format(ppath))
        run('./configure --prefix {0};make'.format(ppath))
        ppath = '{0}/bin/python{1}'.format(ppath,APP_PYTHON_VERSION)
    env.PYTHON = ppath


@task
def virtualenv_setup():
    """
        setup virtualenv with the detected or newly installed python
        """

    set_env()

    ppath = check_python()
    if not ppath:
        python_setup()
    else:
        env.PYTHON = ppath

    if not check_dir(env.APP_DIR_ABS):
        with cd('/tmp'):
            print "### CREATING VIRTUAL ENV ###"
            run('wget {0}'.format(VIRTUALENV_URL))
            vbase = VIRTUALENV_URL.split('/')[-1]
            run('tar -xzf {0}'.format(vbase))
            run('cd {0}; {1} virtualenv.py {2}'.format(vbase.split('.tar.gz')[0],
                                                       env.PYTHON, env.APP_DIR_ABS))
            run('rm -rf virtualenv*')

def install_sources_if_necessary():

    # If this file is not present in the host,
    # or if it is cannot be written by the current user
    # means we need to get the sources so we can build them
    # without problems
    fabfile = os.path.abspath(__file__)
    localDir = os.path.dirname(fabfile)
    sourcesWritable = False
    if exists(fabfile):
        try:
            append(fabfile, '')
            sourcesWritable = True
        except FabricException:
            pass

    if not sourcesWritable:
        with cd('/tmp'):
            local('cd {0} && \
                   tar cjf /tmp/dfms-packedFromSource.tar.bz2 \
                   --exclude BIG_FILES --exclude .git \
                   --exclude build --exclude dist \
                   --exclude *.pyc --exclude dfms.egg-info \
                   {1}'.format(os.path.dirname(localDir), os.path.basename(localDir)))
            put('/tmp/dfms-packedFromSource.tar.bz2', '/tmp/dfms.tar.bz2')
            run('tar xf dfms.tar.bz2 && rm dfms.tar.bz2')
            local('rm /tmp/dfms-packedFromSource.tar.bz2')
            env.srcdir = '/tmp/dfms'
    else:
        env.srcdir = localDir

def install_egg():
    setuptools_cmd('install')

def uninstall_egg():
    virtualenv('/usr/bin/yes | pip uninstall {0}'.format(PROJECT))

def build_egg():
    setuptools_cmd('bdist_egg')

def invoke_tests():
    setuptools_cmd('test')

def setuptools_cmd(cmd):
    install_sources_if_necessary()
    with cd(env.srcdir):
        virtualenv_nocd('python setup.py {0}'.format(cmd))




@task
def build():
    """
        build package binary as an egg
        """
    set_env()
    virtualenv_setup()
    print "### BUILDING ###"
    build_egg()


@task
def build_install():
    """
        build package binary as an egg and install within virtual environment
        """
    build()
    print "### INSTALLING ###"
    install_egg()


@task
def uninstall():
    """
        uninstall package egg from virtual environment
        """
    print "### UNINSTALLING ###"
    set_env()
    virtualenv_setup()
    uninstall_egg()


@task
def run_tests():
    """
        build, install and run tests within virtual environment
        """
    build_install()

    print "### RUNNING TESTS ###"
    invoke_tests()

@task
def run_luigi_dataflow():
    build_install()
    reploc = os.path.dirname(os.path.abspath(__file__))
    virtualenv("cd {0}; pip install luigi; pip install bottle; pip install paste".format(reploc))

@task
def run_chiles_transform():
    build_install()

    reploc = os.path.dirname(os.path.abspath(__file__))
    inp = '/mnt/chiles/20140108_951_2_FINAL_PRODUCTS/13B-266.sb25387671.eb28616143.56665.27054978009_calibrated_deepfield.ms'
    out = '/mnt/chiles-output/split_vis'
    work = '/mnt/chiles-output'
    bindir = '/home/jenkins/casa-release-4.4.0-el6/bin'
    virtualenv('cd {0}; python {0}/test/integrate/freq_split.py -i {1} -o {2} -k {3} -c {4}'.format(reploc, inp, out, work, bindir))

@task
def run_chiles_imaging():
    build_install()
    reploc = os.path.dirname(os.path.abspath(__file__))
    virtualenv('cd {0}/test/integrate/chiles/; python chilesdoapp.py'.format(reploc))

@task
def virtualenv_clean():
    """
        remove virtualenv
        """
    set_env()

    print "### REMOVING VIRTUAL ENV ###"

    run('rm -rf {0}'.format(env.APP_DIR_ABS))