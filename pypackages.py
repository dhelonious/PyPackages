# encoding: utf-8
# pylint: disable=attribute-defined-outside-init

"""
https://www.python.org/dev/peps/pep-0582/
"""

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
from .lib.thread_progress import ThreadProgress


def log(msg):
    if not msg == "":
        print("[PyPackages] {}".format(msg))

def debug_log(msg):
    if sublime.load_settings("pypackages.sublime-settings").get("debug", False):
        if not msg == "":
            log("[DEBUG] {}".format(msg))

def execute(cmd, env=None, cwd=None):
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

def pip(args, env=None, cwd=None):
    python = python_executable()
    pip_cmd = [python, "-m", "pip"] + args

    debug_log(pip_cmd)
    stdout, stderr = execute(
        pip_cmd,
        env=env,
        cwd=cwd,
    )
    if stderr:
        log("[Pypackages] Command \"{}\" failed".format(" ".join(pip_cmd)))
        debug_log(stderr.decode())

    return stdout, stderr

def python_executable():
    settings = sublime.load_settings("pypackages.sublime-settings")
    return settings.get("python_executable").get(sublime.platform())

def python_version():
    stdout, stderr = execute(
        [python_executable(), "--version"],
        env=os.environ,
    )
    if stderr:
        raise PyPackagesError(stderr.decode())

    return re.search("Python ([0-9]*\.[0-9]*)", stdout.decode()).group(1)

def python_executable_path():
    python = python_executable()
    path = shutil.which(python)
    return os.path.dirname(path if path else python)

def pkg_list(packages_path):
    pkg_path = pkg_resources.Environment([packages_path], python=python_version())

    packages = []
    for version in pkg_path:
        for package in pkg_path[version]:
            packages.append("{}=={}".format(package.project_name, package.version))

    if not packages:
        sublime.status_message("No packages found")

    return packages

def project_path(window=None):
    if not window:
        window = sublime.active_window()
    return window.extract_variables().get("project_path", ".")

def pypackages_path(window=None):
    if not window:
        window = sublime.active_window()

    pypackages_root = window.active_view().settings().get(
        "pypackages_root", project_path(window)
    )
    pypackages_root = sublime.expand_variables(
        pypackages_root, window.extract_variables()
    )

    debug_log("pypackages_root: {}".format(pypackages_root))

    return os.path.join(pypackages_root, "__pypackages__")

def pypackages_lib_path(window=None):
    if not window:
        window = sublime.active_window()

    return os.path.join(pypackages_path(window), python_version(), "lib")


class PyPackagesError(Exception):
    pass


class PypackagesCommand(sublime_plugin.WindowCommand):

    def _get_project_path(self):
        return project_path(self.window)

    def _get_pypackages_path(self):
        return pypackages_path(self.window)

    def _get_pypackages_lib_path(self):
        return pypackages_lib_path(self.window)

    def _get_env(self, env=None):
        if not env:
            env = os.environ

        path = env.get("PATH", "")
        pythonpath = env.get("PYTHONPATH", "")
        env["PYPACKAGESPATH"] = self._get_pypackages_lib_path()
        pypackages = os.pathsep.join([".", env["PYPACKAGESPATH"]])

        if not pythonpath.startswith(pypackages):
            env["PYTHONPATH"] = os.pathsep.join(
                [pypackages, pythonpath]
            )

        python_path = python_executable_path()
        if not path.startswith(python_path):
            # Adds an additional pathsep to make the change trackable
            env["PATH"] = os.pathsep.join(
                [python_path, "", path]
            )

        return env


class PypackagesProjectCommand(PypackagesCommand):
    def is_enabled(self):
        return bool(self._get_project_path() and os.getenv("PYPACKAGESPATH"))


class ProjectEnvironmentListener(sublime_plugin.EventListener):
    def __init__(self, *args, **kwds):
        super(ProjectEnvironmentListener, self).__init__(*args, **kwds)

        self.active_project = None
        self.pypackages = None

    def on_activated(self, view):
        if os.getenv("PYPACKAGESPATH"):
            view.set_status("pypackages", "__pypackages__")
        else:
            view.erase_status("pypackages")

        active_project = sublime.active_window().project_file_name()
        if active_project == self.active_project:
            return
        else:
            self.active_project = active_project
            if sublime.load_settings("pypackages.sublime-settings").get("auto_toggle"):
                if self.active_project and os.path.exists(pypackages_path()):
                    threading.Thread(target=self._enable_pypackages).start()
                else:
                    threading.Thread(target=self._disable_pypackages).start()

    def _enable_pypackages(self):
        sublime.active_window().run_command("enable_pypackages")

    def _disable_pypackages(self):
        sublime.active_window().run_command("disable_pypackages")


class EnablePypackagesCommand(PypackagesCommand):
    def run(self):
        if self._get_project_path():
            if os.getenv("PYPACKAGESPATH"):
                return

            sublime.status_message("PyPackages enabled")
            sublime.active_window().active_view().set_status("pypackages", "__pypackages__")
            log("Set local environment")

            os.environ = self._get_env()

            debug_log("PYPACKAGESPATH=\"{}\"".format(os.getenv("PYPACKAGESPATH", "")))
            debug_log("PYTHONPATH=\"{}\"".format(os.getenv("PYTHONPATH", "")))
            debug_log("PATH=\"{}\"".format(os.getenv("PATH", "")))
        else:
            sublime.status_message("No project")
            log("No project")

    def is_visible(self):
        return bool(self._get_project_path() and not os.getenv("PYPACKAGESPATH"))


class DisablePypackagesCommand(PypackagesCommand):
    def run(self):
        if not os.getenv("PYPACKAGESPATH"):
            return

        sublime.status_message("PyPackages disabled")
        sublime.active_window().active_view().erase_status("pypackages")
        log("Unset local environment")

        del os.environ["PYPACKAGESPATH"]

        os.environ["PYTHONPATH"] = re.sub(
            r".{pathsep}.*__pypackages__{sep}[0-9]+\.[0-9]+{sep}lib{pathsep}"
            .format(sep=os.sep, pathsep=os.pathsep),
            "",
            os.getenv("PYTHONPATH", "")
        )

        # Uses the additional pathseps to find the correct paths
        os.environ["PATH"] = os.getenv("PATH", "").replace(
            python_executable_path() + os.pathsep + os.pathsep, "", 1
        )

        debug_log("PYPACKAGESPATH=\"{}\"".format(os.getenv("PYPACKAGESPATH", "")))
        debug_log("PYTHONPATH=\"{}\"".format(os.getenv("PYTHONPATH", "")))
        debug_log("PATH=\"{}\"".format(os.getenv("PATH", "")))

    def is_visible(self):
        return bool(self._get_project_path() and os.getenv("PYPACKAGESPATH"))


class PypackagesInstallCommand(PypackagesProjectCommand):
    def run(self, upgrade=False):
        if upgrade:
            threading.Thread(target=self._list).start()
        else:
            self.window.show_input_panel(
                "Packages:", "", self._install, None, None
            )

    def _install(self, packages, upgrade=False):
        thread = threading.Thread(target=self._install_thread, args=[packages, upgrade])
        thread.start()
        ThreadProgress(thread, "pip install", "")

    def _install_thread(self, packages, upgrade):
        install_args = ["install", "--target", self._get_pypackages_lib_path()]
        install_args += packages.split()
        if upgrade:
            install_args += ["--upgrade"]

        stdout, stderr = pip(
            install_args, env=self._get_env(), cwd=self._get_project_path()
        )
        if stderr:
            for line in stderr.decode().split(os.linesep):
                if "--upgrade" in line:
                    pattern = r"{}([^\s]*)".format(
                        (self._get_pypackages_lib_path() + os.sep)
                        .replace("\\", "\\\\")
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
        self.packages = pkg_list(self._get_pypackages_lib_path())
        self.window.show_quick_panel(self.packages, self._upgrade)


class PypackagesListCommand(PypackagesProjectCommand):
    def run(self):
        if os.path.exists(self._get_pypackages_path()):
            threading.Thread(target=self._list).start()
        else:
            sublime.status_message("No __pypackages__ directory")

    def _list(self):
        packages = pkg_list(self._get_pypackages_lib_path())
        self.window.show_quick_panel(packages, None)


class PypackagesUninstallCommand(PypackagesProjectCommand):
    def run(self):
        if os.path.exists(self._get_pypackages_path()):
            threading.Thread(target=self._list).start()
        else:
            sublime.status_message("No __pypackages__ directory")

    def _uninstall(self, package_index):
        if package_index < 0:
            return

        package = self.packages[package_index]
        thread = threading.Thread(target=self._uninstall_thread, args=[package])
        thread.start()
        ThreadProgress(thread, "pip uninstall", "")

    def _uninstall_thread(self, package):

        uninstall_args = ["uninstall", "-y", package.split()[0]]

        stdout, stderr = pip(
            uninstall_args, env=self._get_env(), cwd=self._get_project_path()
        )
        if stderr:
            debug_log(stderr)
        if stdout:
            for line in stdout.decode().split(os.linesep):
                if "Successfully" in line:
                    log(line.strip())

    def _list(self):
        self.packages = pkg_list(self._get_pypackages_lib_path())
        self.window.show_quick_panel(self.packages, self._uninstall)


class PypackagesFreezeCommand(PypackagesProjectCommand):
    def run(self):
        if os.path.exists(self._get_pypackages_path()):
            self.window.show_input_panel(
                "Target:", "requirements.txt", self._freeze, None, None
            )
        else:
            sublime.status_message("No __pypackages__ directory")

    def _freeze(self, filename):
        sublime.status_message("Freezing pip packages...")

        with open(filename, "w") as target:
            for package in pkg_list(self._get_pypackages_lib_path()):
                debug_log(package)
                print(package, file=target)
