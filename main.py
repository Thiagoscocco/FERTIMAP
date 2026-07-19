from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import venv


PROJECT_ROOT = Path(__file__).resolve().parent
REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"
BOOTSTRAP_VENV = PROJECT_ROOT / ".venv-local"
REQUIRED_MODULES = ("ttkbootstrap",)


def _venv_python_path(venv_path: Path) -> Path:
    if sys.platform.startswith("win"):
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _missing_modules() -> list[str]:
    return [
        module_name
        for module_name in REQUIRED_MODULES
        if importlib.util.find_spec(module_name) is None
    ]


def _interpreter_has_requirements(python_path: Path) -> bool:
    if not python_path.exists():
        return False
    check_command = [
        str(python_path),
        "-c",
        (
            "import importlib.util, sys; "
            "missing = [name for name in sys.argv[1:] "
            "if importlib.util.find_spec(name) is None]; "
            "raise SystemExit(0 if not missing else 1)"
        ),
        *REQUIRED_MODULES,
    ]
    result = subprocess.run(check_command, check=False)
    return result.returncode == 0


def _reexec_with(python_path: Path) -> None:
    raise SystemExit(
        subprocess.call([str(python_path), str(PROJECT_ROOT / "main.py")])
    )


def _bootstrap_runtime() -> None:
    if not _missing_modules():
        return

    for env_dir in (PROJECT_ROOT / ".venv", BOOTSTRAP_VENV):
        env_python = _venv_python_path(env_dir)
        if _interpreter_has_requirements(env_python):
            _reexec_with(env_python)

    env_python = _venv_python_path(BOOTSTRAP_VENV)
    if not env_python.exists():
        print(
            "Dependencias ausentes. Criando ambiente virtual local em '.venv-local'...",
            file=sys.stderr,
        )
        venv.EnvBuilder(with_pip=True).create(BOOTSTRAP_VENV)

    print("Instalando dependencias do projeto...", file=sys.stderr)
    subprocess.run(
        [str(env_python), "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        check=True,
    )
    _reexec_with(env_python)


def main() -> None:
    _bootstrap_runtime()
    from ui.main_window import FerticalcApp

    app = FerticalcApp()
    app.run()


if __name__ == "__main__":
    main()
