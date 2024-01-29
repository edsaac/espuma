from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
import subprocess
from functools import partial, cached_property
from typing import Any, Optional
import os
from shutil import rmtree

from math import isclose
from pyvista import POpenFOAMReader

import warnings

### Run as subprocess: ###############################
run = partial(subprocess.run, capture_output=True, text=True, encoding="utf-8")
run_solver = partial(
    subprocess.run,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
    encoding="utf-8",
)
### Run as subprocess: ###############################


@dataclass(slots=True, frozen=True)
class Dimension:
    mass: int = 0
    length: int = 0
    time: int = 0
    temperature: int = 0
    moles: int = 0
    current: int = 0
    luminous: int = 0

    @classmethod
    def from_bracketed(cls, text: str):
        return Dimension(
            *[
                int(d)
                for d in text.strip()
                .removeprefix("[")
                .removesuffix("]")
                .strip()
                .split()
            ]
        )

    def __str__(self) -> str:
        return f"[{self.mass} {self.length} {self.time} {self.temperature} {self.moles} {self.current} {self.luminous}]"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                [
                    f"{k}={getattr(self, k)}"
                    for k in self.__slots__
                    if getattr(self, k) != 0
                ]
            )
            + ")"
        )


class OpenFoam_Dict(dict):
    """
    Inhereting from dict to avoid triggering __setitem__ and
    __getitem__ methods during initialization.
    """

    def __getitem__(self, key: str) -> Any:
        # print(f"Calling the {type(self).__name__} getittem for {key}")
        if "." in key:
            prekey, poskey = key.split(".", maxsplit=1)
            return self[prekey][poskey]
        else:
            return super().__getitem__(key)

    def __setitem__(self, key: Any, value: Any) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} does not accept setting items.\n"
            "Use the OpenFoam_File __setitem__ instead"
        )

    def __delitem__(self, key: Any, value: Any) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} does not allow deleting items.\n"
            "Use the OpenFoam_File __delitem__ instead"
        )

    def __repr__(self) -> str:
        return super().__repr__()

    def _repr_html_(self) -> str:
        vreprs = [
            v._repr_html_() if hasattr(v, "_repr_html_") else str(v)
            for v in self.values()
        ]

        return (
            "<ul>\n"
            + "".join(
                [f"<li><b>{k}:</b> {v}</li>\n" for k, v in zip(self.keys(), vreprs)]
            )
            + "</ul>"
        )


class File:
    def __init__(self, path: str | Path) -> None:
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError("File does not exist")

        if not path.is_file():
            raise FileNotFoundError("Path is not file")

        self.path = path

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path})"


class OpenFoam_File(File):
    """
    Base class for openFOAM files.
    """

    def __init__(self, path: str | Path) -> None:
        super().__init__(path)

    def __setitem__(self, key: Any, item: Any) -> None:
        self._foamDictionary_set_value(key, item)

    def __getitem__(self, key: Any) -> Any:
        # print(f"Calling the {type(self).__name__} getittem for {key}")
        return self.foamDictionary_generate_dict(key)

    def __delitem__(self, key):
        return self._foamDictionary_del_value(key)

    def _repr_html_(self):
        return (
            "<details open>\n"
            f"<summary><b>{self.path.name}</b></summary>\n"
            "<ul style='list-style: none;'>"
            + "\n".join([f"<li>{k}</li>\n" for k in self.keys()])
            + "\n</ul>\n"
            "</details>\n"
        )

    def _foamDictionary_del_value(self, entry):
        command = [
            "foamDictionary",
            str(self.path),
            "-entry",
            entry,
            "-remove",
            "-disableFunctionEntries",
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode == 0:
            return value.stdout.strip()
        else:
            raise ValueError(" ".join(command) + "\n\n" + value.stderr.strip())

    def _foamDictionary_get_value(self, entry):
        command = [
            "foamDictionary",
            str(self.path),
            "-entry",
            entry,
            "-value",
            "-disableFunctionEntries",
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode == 0:
            return value.stdout.strip()
        else:
            raise ValueError(" ".join(command) + "\n\n" + value.stderr.strip())

    def foamDictionary_generate_dict(self, entry: Optional[str] = None):
        command = [
            "foamDictionary",
            str(self.path),
            "-keywords",
            "-disableFunctionEntries",
        ]
        if entry:
            command.extend(("-entry", entry))

        output = run(command, cwd=self.path.parent)

        if output.returncode == 0:
            foamEntry = OpenFoam_Dict(
                (k, self.foamDictionary_generate_dict(f"{entry}.{k}"))
                for k in output.stdout.strip().splitlines()
            )

        else:
            foamEntry = self._foamDictionary_get_value(entry)

        return foamEntry

    def _foamDictionary_set_value(self, entry, value):
        """
        Entry corresponds to the name.key of the dictionary
        """
        command = [
            "foamDictionary",
            str(self.path),
            "-entry",
            entry,
            "-set",
            str(value),
            "-disableFunctionEntries",
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode != 0:
            raise ValueError(" ".join(command), value.stderr.strip())

    def items(self):
        return [(k, self[k]) for k in self.keys()]

    def keys(self):
        return self._keywords

    def values(self):
        return self.items().values()

    @cached_property
    def _keywords(self):
        command = [
            "foamDictionary",
            str(self.path),
            "-keywords",
            "-disableFunctionEntries",
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode == 0:
            return value.stdout.strip().split()


class Dict_File(OpenFoam_File):
    """
    Class for openFOAM files than store directories.
    """

    def __init__(self, path: str | Path):
        super().__init__(path)

    def _repr_html_(self):
        head = (
            "<details open>\n"
            f"<summary><b>{self.path.name}</b></summary>\n"
            "<ul style='list-style: none;'>\n"
        )

        body = ""
        for key, value in self.items():
            if hasattr(value, "_repr_html_"):
                vrprs = value._repr_html_()
            else:
                vrprs = repr(value)

            body += f"<li><b>{key}</b>: {vrprs}</li>\n"

        tail = "</ul>\n" "</details>\n"

        return head + body + tail


class Field_File(OpenFoam_File):
    def __init__(self, path: str | Path):
        super().__init__(path)

    @cached_property
    def dimensions(self):
        value = self._foamDictionary_get_value("dimensions")
        return Dimension.from_bracketed(value)

    @cached_property
    def boundaryField(self):
        return self.foamDictionary_generate_dict("boundaryField")

    @cached_property
    def internalField(self):
        return self.foamDictionary_generate_dict("internalField")


class Directory:
    def __init__(self, path: str | Path):
        path = Path(path).absolute()

        if not path.exists():
            raise FileNotFoundError(f"{path} does not exist")

        if not path.is_dir():
            raise NotADirectoryError(f"{path} is not a directory")

        self.path = path

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path})"

    def _repr_html_(self):
        return (
            "<details open>\n"
            f"<summary><b>{self.path.name}</b></summary>\n"
            "<ul>"
            + "\n".join([f"<li>{f.name}</li>\n" for f in self._files])
            + "\n</ul>\n"
            "</details>\n"
        )

    @property
    def _files(self):
        return [f for f in self.path.iterdir() if f.is_file()]

    @property
    def files(self):
        return [str(f) for f in self._files]


class Zero_Directory(Directory):
    def __init__(self, path: str | Path):
        super().__init__(path)

        ## Add fields as properties
        for f in self._files:
            setattr(self, f.name, Field_File(f))


class Constant_Directory(Directory):
    def __init__(self, path: str | Path):
        super().__init__(path)

        ## Add files in directory as properties
        for f in self._files:
            setattr(self, f.name, Dict_File(f))


class System_Directory(Directory):
    def __init__(self, path: str | Path):
        super().__init__(path)

        ## Add file directories as properties
        for f in self._files:
            setattr(self, f.name, Dict_File(f))

        assert getattr(self, "controlDict")


class Case_Directory(Directory):
    def __init__(self, path: str | Path) -> None:
        super().__init__(path)

        # Identify zero folder
        n_valid_zero_folders = 0
        for zero in self.path.glob(r"0*"):
            if float(zero.name) == 0:
                n_valid_zero_folders += 1

                if n_valid_zero_folders > 1:
                    raise FileExistsError("More than one zero folder was found.")

                self.zero = Zero_Directory(zero)

        self.constant = Constant_Directory(self.path / "constant")
        self.system = System_Directory(self.path / "system")

    def _repr_html_(self):
        return (
            "<details open>\n"
            f"<summary><b>{self.path.name}</b></summary>\n"
            "<ul style='list-style: none;'>\n"
            "<li>" + self.zero._repr_html_() + "</li>\n"
            "<li>" + self.constant._repr_html_() + "</li>\n"
            "<li>" + self.system._repr_html_() + "</li>\n"
            "</ul>\n"
            "</details>\n"
        )

    def get_vtk_reader(self):
        # Dummy file for Paraview visualization avoiding foamToVTK
        # Source: https://openfoamwiki.net/index.php?title=Case_Name_.foam_File&oldid=18024
        pvfoam = Path(self.path / "espuma.foam")
        pvfoam.touch()

        return POpenFOAMReader(pvfoam)

    @property
    def list_times(self):
        return sorted([float(t) for t in self._foamListTimes()])

    def is_finished(self):
        if self.system.controlDict["stopAt"] != "endTime":
            raise TypeError(  # > Find a better exception
                "Case not set up to stop at an endTime."
            )

        end_time = float(self.system.controlDict["endTime"])
        latest_time = self.list_times[-1]

        return isclose(end_time, latest_time)

    def _blockMesh(self):
        command = ["blockMesh"]

        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(
                " ".join(command)
                + "\n\n"
                + value.stdout.strip()
                + "\n\n"
                + value.stderr.strip()
            )

        print("blockMesh finished successfully!")

    def _setFields(self):
        command = ["setFields"]

        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(
                " ".join(command)
                + "\n\n"
                + value.stdout.strip()
                + "\n\n"
                + value.stderr.strip()
            )

        print("setFields finished successfully!")

    def _runCase(self):
        application = self.system.controlDict["application"]
        command = [application]

        value = run_solver(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        print(f"{application} finished successfully!")

    def _foamListTimes(self):
        command = ["foamListTimes", "-withZero"]
        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        return value.stdout.strip().splitlines()

    def _foamListTimes_remove(self):
        command = ["foamListTimes", "-rm"]
        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        print(" ".join(command) + " finished successfully!")

    @classmethod
    def clone_from_template(
        cls, template: Case_Directory, path: str | Path, overwrite: bool = False
    ):
        if not isinstance(template, Case_Directory):
            raise TypeError(f"{template} must be a espuma.Case_Directory object")

        path = Path(path)

        if path.exists():
            if not overwrite:
                raise OSError(
                    f"{path} already exists.\n" "Maybe you want to set overwrite=True?"
                )

            if path.is_dir():
                rmtree(path)

            elif path.is_file():
                path.unlink()

        cls._foamCloneCase(template.path, path)

        return Case_Directory(path)

    @classmethod
    def _foamCloneCase(cls, source_case: str | Path, target_case: str | Path):
        command = ["foamCloneCase", str(source_case), str(target_case)]
        value = run(command)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        print(" ".join(command) + " finished successfully!")


def main():
    pass


if __name__ == "__main__":
    main()

else:
    ## Check that OpenFOAM is installed
    assert "FOAM_APP" in os.environ

    ## Add espuma shell scripts to path
    if os.name == "posix":
        os.environ["ESPUMA_SCRIPTS"] = str(
            (Path(__file__).parent / "scripts").absolute()
        )

    else:
        warnings.warn("boundaryProbe parsing script not supported")
