"""Entry without bash: `python <skill-dir>/scripts/wi.py ...` sets up .venv itself and reruns inside it.

Same rules as scripts/wi (keep the two in sync): .installed records where the venv was built, a moved or
stale venv is rebuilt from scratch, a failed install leaves nothing behind, a non-venv folder is never wiped.
Needed where bash is missing, e.g. Windows without Git Bash.
"""
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REQ = SKILL_DIR / "requirements.txt"
EXIT_ENV, EXIT_NETWORK = 1, 4


def _fail(msg, code):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def _venv_python(path):
    win = path / "Scripts" / "python.exe"
    return win if win.exists() else path / "bin" / "python"


def _ready(path):
    marker = path / ".installed"
    return (marker.exists() and marker.stat().st_mtime >= REQ.stat().st_mtime
            and marker.read_text().strip() == str(path) and _venv_python(path).exists())


def venv_path():
    """Same default as scripts/wi: <skill-dir>/.venv, or a short per-user path on Windows (260-character limit)."""
    if os.environ.get("WI_VENV"):
        return Path(os.environ["WI_VENV"])
    return Path.home() / ".cache" / "wiki-interest" / "venv" if os.name == "nt" else SKILL_DIR / ".venv"


def run():
    """Rerun wi.py inside the skill's venv, creating it first if needed. Never returns."""
    if sys.version_info < (3, 10):
        _fail("Python 3.10+ is needed, this is " + sys.version.split()[0] + ". Install it from python.org.", EXIT_ENV)
    path = venv_path()
    if not _ready(path):
        if path.is_dir() and any(path.iterdir()) and not (path / "pyvenv.cfg").exists():
            _fail(f"{path} exists and is not a Python venv; refusing to overwrite it. Set WI_VENV to a new folder.",
                  EXIT_ENV)
        print(f"[wi] first run: creating {path} and installing dependencies (1-2 min)...", file=sys.stderr)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            venv.EnvBuilder(clear=True, with_pip=True).create(path)
        except Exception as e:  # noqa: BLE001 - any failure here means the same fix
            _fail(f"could not create a venv ({e}). Reinstall Python from python.org with pip included.", EXIT_ENV)
        pip = subprocess.run([str(_venv_python(path)), "-m", "pip", "install", "--quiet",
                              "--disable-pip-version-check", "-r", str(REQ)], stdout=sys.stderr)
        if pip.returncode:
            shutil.rmtree(path, ignore_errors=True)
            _fail(f"could not install the dependencies in {REQ} (see pip's output above): no internet access or a "
                  "broken Python install. Run the same command once more; nothing is kept from a failed install. "
                  "If it fails again, tell the user the analysis could not run and why, and stop: do not answer "
                  "from general knowledge.", EXIT_NETWORK)
        (path / ".installed").write_text(str(path))
    env = dict(os.environ, PYTHONIOENCODING="utf-8",
               WI_CMD=f'"{Path(sys.executable).as_posix()}" "{(SKILL_DIR / "scripts" / "wi.py").as_posix()}"')
    sys.exit(subprocess.run([str(_venv_python(path)), str(SKILL_DIR / "scripts" / "wi.py"), *sys.argv[1:]],
                            env=env).returncode)
