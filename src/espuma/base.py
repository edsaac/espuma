from pathlib import Path
from dataclasses import dataclass
import subprocess
from functools import partial, cached_property, cache
from typing import Any
import os

run = partial(subprocess.run, capture_output=True, text=True, encoding="utf-8")


@dataclass(slots=True)
class Dimension:
    mass: int
    length: int
    time: int
    temperature: int = 0
    moles: int = 0
    current: int = 0
    luminous: int = 0

    @classmethod
    def from_bracketed(cls, text: str):
        return Dimension(
            *(text.strip().removeprefix("[").removesuffix("]").strip().split())
        )

    def __str__(self) -> str:
        return f"[{self.mass} {self.length} {self.time} {self.temperature} {self.moles} {self.current} {self.luminous}]"


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
            f"{type(self).__name__} does not accept setting items."
            "Use OpenFoam_File setter instead"
        )

    def __repr__(self) -> str:
        return super().__repr__()


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

    def __init__(self, path: str | Path):
        super().__init__(path)

    def __setitem__(self, key: Any, item: Any) -> Any:
        return self._foamDictionary_set_value(key, item)

    def __getitem__(self, key: Any) -> Any:
        # print(f"Calling the {type(self).__name__} getittem for {key}")
        return self.foamDictionary_generate_dict(key)

    def _foamDictionary_get_value(self, entry):
        command = ["foamDictionary", str(self.path), "-entry", entry, "-value"]
        value = run(command, cwd=self.path.parent)

        if value.returncode == 0:
            return value.stdout.strip()
        else:
            raise ValueError(" ".join(command) + "\n\n" + value.stderr.strip())

    def foamDictionary_generate_dict(self, entry: str | None = None):
        command = ["foamDictionary", str(self.path), "-keywords"]
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
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode != 0:
            raise ValueError(" ".join(command), value.stderr.strip())

    @cache
    def items(self):
        return {k: self[k] for k in self.keys()}

    def keys(self):
        return self._keywords

    def values(self):
        return self.items().values()

    @cached_property
    def _keywords(self):
        command = ["foamDictionary", str(self.path), "-keywords"]
        value = run(command, cwd=self.path.parent)

        if value.returncode == 0:
            return value.stdout.strip().split()


class Dict_File(OpenFoam_File):
    """
    Class for openFOAM files than store directories.
    """

    def __init__(self, path: str | Path):
        super().__init__(path)


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
        path = Path(path)

        if not path.exists:
            raise FileNotFoundError(f"{path} does not exist")

        if not path.is_dir:
            raise NotADirectoryError(f"{path} is not a directory")

        self.path = path

    def __str__(self) -> str:
        return str(self.path)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.path})"

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

        self.zero = Zero_Directory(self.path / "0")
        self.constant = Constant_Directory(self.path / "constant")
        self.system = System_Directory(self.path / "system")


def main():
    PATH = "/home/edsaa/foam/cavity"
    d = Case_Directory(PATH)

    print(d.constant.transportProperties)
    print(d.constant.transportProperties.FoamFile)
    print(d.constant.transportProperties["nu"])

    print(d.constant.transportProperties["nu"])
    print(d.system.fvSolution.FoamFile.items())

    # d.system.fvSolution["solvers.p.solver"] = "HEHE"

    # print(d.system.fvSolution["solvers"]["p"]["solver"])

    # print(d.zero.p.dimensions)
    # for f in d.zero.files:
    #     print(f, f.dimensions)
    #     print(f, f.FoamFile)

    # print(d.zero.p.FoamFile)
    # print(d.zero.U.boundaryField)

    # print(d.zero.files["p"])
    # print(d.zero.files["p"].case_dir)

    # print(d.zero.files["p"].get_keywords())
    # print(d.zero.files["p"].get_value_from_foamDictionary("boundaryField"))
    # print(d.system)


if __name__ == "__main__":
    main()

else:
    assert "FOAM_APP" in os.environ
