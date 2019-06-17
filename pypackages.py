# encoding: utf-8
# pylint: disable=attribute-defined-outside-init

# TODO: Improve usage of `status_message`
# TODO: Improve error handling and logging

import os
import re
import shutil
import subprocess
import threading

import sublime
import sublime_plugin

# pylint: disable=relative-beyond-top-level
from .lib import pkg_resources


def log(msg):
    if not msg == "":
        print("[PyPackages] {}".format(msg))

def debug_log(msg):
    if sublime.load_settings("pypackages.sublime-settings").get("debug", False):
        if not msg == "":
            log("[DEBUG] {}".format(msg))

class PyPackagesError(Exception):
    pass

class PypackagesCommand(sublime_plugin.WindowCommand):
    pass

class PypackagesProjectCommand(PypackagesCommand):
    def is_enabled(self):
        return bool(_get_project_path() and os.getenv("PYPACKAGES"))


def _execute(cmd, env=None, cwd=None):
    stdout, stderr = subprocess.Popen(
        cmd,
        env=env,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=sublime.platform()=="windows",
    ).communicate()

    debug_log("stdout: {}".format(stdout.decode()))
    debug_log("stderr: {}".format(stderr.decode()))

    return stdout, stderr

def _pip(args, env=None):
    python = _get_python_executable()
    pip_cmd = [python, "-m", "pip"] + args

    debug_log(pip_cmd)
    stdout, stderr = _execute(
        pip_cmd,
        env=env,
        cwd=_get_project_path(),
    )
    if stderr:
        log("[Pypackages] Command \"{}\" failed".format(" ".join(pip_cmd)))
        debug_log(stderr.decode())

    return stdout, stderr

def _pkg_list(packages_path):
    pkg_path = pkg_resources.Environment([packages_path])

    packages = []
    for version in pkg_path:
        for package in pkg_path[version]:
            packages.append("{}=={}".format(package.project_name, package.version))

    if not packages:
        sublime.status_message("No packages found")

    return packages


# TODO: Include into `sublime.WindowCommand` class
def _get_python_executable():
    settings = sublime.load_settings("pypackages.sublime-settings")
    return settings.get("python_executable").get(sublime.platform())

# TODO: Include into `sublime.WindowCommand` class
def _get_python_executable_path():
    python_executable = _get_python_executable()
    path = shutil.which(python_executable)
    return os.path.dirname(path if path else python_executable)

# TODO: Include into `sublime.WindowCommand` class
def _get_project_path():
    return sublime.active_window().extract_variables().get("project_path", ".")

# TODO: Include into `sublime.WindowCommand` class
def _get_pypackages_path():
    """Return local __pypackages__ path relative to the script being run

    See https://www.python.org/dev/peps/pep-0582/
    """
    window = sublime.active_window()
    view = window.active_view()

    debug_log(view.settings().has("pypackages_root"))
    pypackages_root = view.settings().get(
        "pypackages_root", _get_project_path()
    )
    pypackages_root = sublime.expand_variables(
        pypackages_root, window.extract_variables()
    )

    debug_log("pypackages_root: {}".format(pypackages_root))

    return os.path.join(pypackages_root, "__pypackages__")

# TODO: Include into `sublime.WindowCommand` class
def _get_pypackages_lib_path():
    pypackages_path = _get_pypackages_path()

    stdout, stderr = _execute(
        [_get_python_executable(), "--version"],
        env=os.environ,
    )
    if stderr:
        raise PyPackagesError(stderr.decode())

    python_version = re.search("Python ([0-9]*\.[0-9]*)", stdout.decode()).group(1)
    return os.path.join(pypackages_path, python_version, "lib")

# TODO: Include into `sublime.WindowCommand` class
def _get_env(env=None):
    if not env:
        env = os.environ

    path = env.get("PATH", "")
    pythonpath = env.get("PYTHONPATH", "")
    pypackages_path = os.pathsep.join([".", _get_pypackages_lib_path()])

    env["PYPACKAGES"] = pypackages_path

    if not pythonpath.startswith(pypackages_path):
        env["PYTHONPATH"] = os.pathsep.join(
            [pypackages_path, pythonpath]
        )

    python_path = _get_python_executable_path()
    if not path.startswith(python_path):
        # Adds an additional pathsep to make the change trackable
        env["PATH"] = os.pathsep.join(
            [python_path, "", path]
        )

    return env


class ProjectEnvironmentListener(sublime_plugin.EventListener):
    def __init__(self, *args, **kwds):
        super(ProjectEnvironmentListener, self).__init__(*args, **kwds)

        self.active_project = None
        self.pypackages = None

    def on_activated(self, view):
        active_project = sublime.active_window().project_file_name()
        if active_project == self.active_project:
            return
        else:
            self.active_project = active_project
            if sublime.load_settings("pypackages.sublime-settings").get("auto_toggle"):
                if self.active_project and os.path.exists(_get_pypackages_path()):
                    threading.Thread(target=self._enable_pypackages).start()
                else:
                    threading.Thread(target=self._disable_pypackages).start()

    def _enable_pypackages(self):
        sublime.active_window().run_command("enable_pypackages")

    def _disable_pypackages(self):
        sublime.active_window().run_command("disable_pypackages")


class EnablePypackagesCommand(sublime_plugin.WindowCommand):
    def run(self):
        if _get_project_path():
            sublime.status_message("PyPackages enabled")
            log("Set local environment")

            os.environ = _get_env()

            debug_log("PYPACKAGES=\"{}\"".format(os.getenv("PYPACKAGES", "")))
            debug_log("PYTHONPATH=\"{}\"".format(os.getenv("PYTHONPATH", "")))
            debug_log("PATH=\"{}\"".format(os.getenv("PATH", "")))
        else:
            sublime.status_message("No project")
            log("No project")

    def is_visible(self):
        return bool(_get_project_path() and not os.getenv("PYPACKAGES"))


class DisablePypackagesCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message("PyPackages disabled")
        log("Unset local environment")

        del os.environ["PYPACKAGES"]

        # TODO: Pathseps are not always removed correctly
        os.environ["PYTHONPATH"] = re.sub(
            ".{pathsep}.*__pypackages__{sep}[0-9]+\.[0-9]+{sep}lib{pathsep}"
            .format(sep=os.sep, pathsep=os.pathsep),
            "",
            os.getenv("PYTHONPATH", "")
        )

        # Uses the additional pathseps to find the correct paths
        os.environ["PATH"] = os.getenv("PATH", "").replace(
            _get_python_executable_path() + os.pathsep + os.pathsep, "", 1
        )

        debug_log("PYPACKAGES=\"{}\"".format(os.getenv("PYPACKAGES", "")))
        debug_log("PYTHONPATH=\"{}\"".format(os.getenv("PYTHONPATH", "")))
        debug_log("PATH=\"{}\"".format(os.getenv("PATH", "")))

    def is_visible(self):
        return bool(_get_project_path() and os.getenv("PYPACKAGES"))

class PypackagesInstallCommand(PypackagesProjectCommand):
    def run(self, upgrade=False):
        if upgrade:
            threading.Thread(target=self._list).start()
        else:
            self.window.show_input_panel("Packages:", "", self._install, None, None)

    def _install(self, packages, upgrade=False):
        sublime.status_message("Installing pip packages...")

        install_args = ["install", "--target", _get_pypackages_lib_path(), packages]
        if upgrade:
            install_args += ["--upgrade"]

        stdout, stderr = _pip(install_args, env=_get_env())
        if stderr:
            for line in stderr.decode().split(os.linesep):
                if "--upgrade" in line:
                    pattern = "{}([^\s]*)".format(
                        (_get_pypackages_lib_path() + os.sep).replace("\\", "\\\\")
                    )
                    log("{} already exists. Upgrade to replace it.".format(
                        re.search(pattern, line).group(1)
                    ))
        elif stdout:
            for line in stdout.decode().split(os.linesep):
                if "Successfully" in line:
                    log(line.strip())

    def _upgrade(self, package_index):
        if package_index < 0:
            return

        package = self.packages[package_index]
        self._install(package.split()[0], upgrade=True)

    def _list(self):
        self.packages = _pkg_list(_get_pypackages_lib_path())
        self.window.show_quick_panel(self.packages, self._upgrade)


class PypackagesListCommand(PypackagesProjectCommand):
    def run(self):
        if os.path.exists(_get_pypackages_path()):
            threading.Thread(target=self._list).start()
        else:
            sublime.status_message("No __pypackages__ directory")

    def _list(self):
        packages = _pkg_list(_get_pypackages_lib_path())
        self.window.show_quick_panel(packages, None)


class PypackagesUninstallCommand(PypackagesProjectCommand):
    def run(self):
        if os.path.exists(_get_pypackages_path()):
            threading.Thread(target=self._list).start()
        else:
            sublime.status_message("No __pypackages__ directory")

    def _uninstall(self, package_index):
        if package_index < 0:
            return

        package = self.packages[package_index]
        uninstall_args = ["uninstall", "-y", package.split()[0]]

        sublime.status_message("Uninstalling pip package...")
        stdout, stderr = _pip(uninstall_args, env=_get_env())
        if stderr:
            debug_log(stderr)
        if stdout:
            for line in stdout.decode().split(os.linesep):
                if "Successfully" in line:
                    log(line.strip())

    def _list(self):
        self.packages = _pkg_list(_get_pypackages_lib_path())
        self.window.show_quick_panel(self.packages, self._uninstall)


class PypackagesFreezeCommand(PypackagesProjectCommand):
    def run(self):
        if os.path.exists(_get_pypackages_path()):
            self.window.show_input_panel("Target:", "requirements.txt", self._freeze, None, None)
        else:
            sublime.status_message("No __pypackages__ directory")

    def _freeze(self, filename):
        sublime.status_message("Freezing pip packages...")

        with open(filename, "w") as target:
            for package in _pkg_list(_get_pypackages_lib_path()):
                target.write(package + os.linesep)
                debug_log(package)
