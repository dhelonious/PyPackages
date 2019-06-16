# encoding: utf-8

# TODO: Improve usage of `status_message`

import os
import re
import shutil
import subprocess
import threading

from .lib import pkg_resources

import sublime
import sublime_plugin


def log(msg):
    print("[pythonloc] {}".format(msg))

def debug_log(msg):
    if sublime.load_settings("pythonloc.sublime-settings").get("debug", False):
        print("[pythonloc] [debug] {}".format(msg))

class PythonlocError(Exception):
    pass

class PythonlocProjectCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return bool(_get_project_path() and os.getenv("PYTHONLOC", False))


def _get_python_executable():
    settings = sublime.load_settings("pythonloc.sublime-settings")
    return settings.get("python_executable").get(sublime.platform())

def _get_python_executable_path():
    return os.path.dirname(shutil.which(_get_python_executable()))

def _get_project_path():
    return sublime.active_window().extract_variables().get("project_path", None)

def _get_pypackages_path():
    """Return local __pypackages__ path relative to the script being run

    See https://www.python.org/dev/peps/pep-0582/
    """
    # TODO: Configurable __pypackages__ location
    return os.path.join(_get_project_path(), "__pypackages__")

def _get_pypackages_lib_path():
    pypackages_path = _get_pypackages_path()

    stdout, stderr = subprocess.Popen(
        [_get_python_executable(), "--version"],
        env=os.environ,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=sublime.platform()=="windows",
    ).communicate()

    if stderr:
        raise PythonlocError(stderr.decode())

    python_version = re.search("Python ([0-9]*\.[0-9]*)", stdout.decode()).group(1)
    return os.path.join(pypackages_path, python_version, "lib")

def _get_env(env=None):
    if not env:
        env = os.environ
    pythonpath = env.get("PYTHONPATH", "")
    pypackages_path = os.pathsep.join([".", _get_pypackages_lib_path()])
    if not pythonpath.startswith(pypackages_path):
        env["PYTHONPATH"] = os.pathsep.join(
            [pypackages_path, pythonpath]
        )
    path = env.get("PATH", "")
    python_path = _get_python_executable_path()
    if not path.startswith(python_path):
        env["PATH"] = os.pathsep.join(
            [python_path, path]
        )
    return env

def _piploc(args, env=None):
    python = _get_python_executable()
    pip_cmd = [python, "-m", "pip"] + args

    debug_log(pip_cmd)
    stdout, stderr = subprocess.Popen(
        pip_cmd,
        env=env,
        cwd=_get_project_path(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=sublime.platform()=="windows",
    ).communicate()

    if stderr:
        log("[Piploc] Command \"{}\" failed".format(" ".join(pip_cmd)))
        debug_log(stderr.decode())

    return stdout, stderr

def _list_packages(packages_path):
    pkg_path = pkg_resources.Environment([packages_path])

    packages = []
    for version in pkg_path:
        for package in pkg_path[version]:
            packages.append("{}=={}".format(package.project_name, package.version))

    if not packages:
        sublime.status_message("No packages found")

    return packages


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
            if sublime.load_settings("pythonloc.sublime-settings").get("auto_toggle"):
                if self.active_project and os.path.exists(_get_pypackages_path()):
                    threading.Thread(target=self._enable_pythonloc).start()
                else:
                    threading.Thread(target=self._disable_pythonloc).start()

    def _enable_pythonloc(self):
        sublime.active_window().run_command("enable_pythonloc")

    def _disable_pythonloc(self):
        sublime.active_window().run_command("disable_pythonloc")


class EnablePythonlocCommand(sublime_plugin.WindowCommand):
    def run(self):
        if _get_project_path():
            sublime.status_message("Pythonloc enabled")
            log("Set local environment")

            env = _get_env()
            env["PYTHONLOC"] = "enabled"
            os.environ = env

            debug_log("PYTHONLOC=\"{}\"".format(os.getenv("PYTHONLOC", "")))
            debug_log("PYTHONPATH=\"{}\"".format(os.getenv("PYTHONPATH", "")))
            debug_log("PATH=\"{}\"".format(os.getenv("PATH", "")))
        else:
            sublime.status_message("No project")
            log("No project")

    def is_visible(self):
        return bool(_get_project_path() and not os.getenv("PYTHONLOC", False))


class DisablePythonlocCommand(sublime_plugin.WindowCommand):
    def run(self):
        sublime.status_message("Pythonloc disabled")
        log("Unset local environment")

        del os.environ["PYTHONLOC"]
        os.environ["PYTHONPATH"] = os.getenv("PYTHONPATH").replace(
            os.pathsep.join([".", _get_pypackages_lib_path(), ""]), "", 1
        )
        os.environ["PATH"] = os.getenv("PATH").replace(
            _get_python_executable_path() + os.pathsep, "", 1
        )

        debug_log("PYTHONLOC=\"{}\"".format(os.getenv("PYTHONLOC", "")))
        debug_log("PYTHONPATH=\"{}\"".format(os.getenv("PYTHONPATH", "")))
        debug_log("PATH=\"{}\"".format(os.getenv("PATH", "")))

    def is_visible(self):
        return bool(_get_project_path() and os.getenv("PYTHONLOC", False))

class PiplocInstallCommand(PythonlocProjectCommand):
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

        stdout, stderr = _piploc(install_args, env=_get_env())
        if stderr:
            for line in stderr.decode().split(os.linesep):
                if "--upgrade" in line:
                    pattern = "{}([^\s]*)".format(
                        (_get_pypackages_lib_path() + os.sep).replace("\\", "\\\\")
                    )
                    package = re.search(pattern, line).group(1)
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
        self.packages = _list_packages(_get_pypackages_lib_path())
        self.window.show_quick_panel(self.packages, self._upgrade)


class PiplocListCommand(PythonlocProjectCommand):
    def run(self):
        if os.path.exists(_get_pypackages_path()):
            threading.Thread(target=self._list).start()
        else:
            sublime.status_message("No __pypackages__ directory")

    def _list(self):
        packages = _list_packages(_get_pypackages_lib_path())
        self.window.show_quick_panel(packages, None)


class PiplocUninstallCommand(PythonlocProjectCommand):
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
        stdout, stderr = _piploc(uninstall_args, env=_get_env())
        if stdout:
            for line in stdout.decode().split(os.linesep):
                if "Successfully" in line:
                    log(line.strip())

    def _list(self):
        self.packages = _list_packages(_get_pypackages_lib_path())
        self.window.show_quick_panel(self.packages, self._uninstall)


class PiplocFreezeCommand(PythonlocProjectCommand):
    def run(self):
        if os.path.exists(_get_pypackages_path()):
            self.window.show_input_panel("Target:", "requirements.txt", self._freeze, None, None)
        else:
            sublime.status_message("No __pypackages__ directory")

    def _freeze(self, filename):
        sublime.status_message("Freezing pip packages...")

        with open(filename, "w") as target:
            for package in _list_packages(_get_pypackages_lib_path()):
                target.write(package + os.linesep)
                debug_log(package)
