from __future__ import annotations

import subprocess
import os

from math import isclose
from pathlib import Path
from dataclasses import dataclass
from functools import partial, cached_property
from typing import Any, Optional
from shutil import rmtree

import numpy as np
import xarray as xr
import pyvista as pv
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
######################################################


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
            *[int(d) for d in text.strip().removeprefix("[").removesuffix("]").strip().split()]
        )

    def __str__(self) -> str:
        return f"[{self.mass} {self.length} {self.time} {self.temperature} {self.moles} {self.current} {self.luminous}]"

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                [f"{k}={getattr(self, k)}" for k in self.__slots__ if getattr(self, k) != 0]
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
            f"{type(self).__name__} does not allow setting items directly.\n"
            "Try setting from an OpenFoam_File instance instead"
        )

    def __delitem__(self, key: Any, value: Any) -> None:
        raise NotImplementedError(
            f"{type(self).__name__} does not allow deleting items directly.\n"
            "Try deleting from an OpenFoam_File instance instead"
        )

    def __repr__(self) -> str:
        return super().__repr__()

    def _repr_html_(self) -> str:
        vreprs = [v._repr_html_() if hasattr(v, "_repr_html_") else str(v) for v in self.values()]

        return (
            "<ul>\n"
            + "".join([f"<li><b>{k}:</b> {v}</li>\n" for k, v in zip(self.keys(), vreprs)])
            + "</ul>"
        )


class OpenFoam_File:
    """
    Base class for openFOAM files.
    """

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

    def __setitem__(self, key: Any, item: Any) -> None:
        self._foamDictionary_set_value(key, item)

        if "_keywords" in self.__dict__:
            del self._keywords

    def __getitem__(self, key: Any) -> Any:
        # print(f"Calling the {type(self).__name__} getittem for {key}")
        return self.foamDictionary_generate_dict(key)

    def __delitem__(self, key) -> None:
        self._foamDictionary_del_value(key)

    def _repr_html_(self):
        head = (
            "<details open>\n"
            "<summary style='font-size: 1.0rem; border-bottom: 1px dashed purple; cursor: pointer;'>"
            f"<span>{self.path.name}</span></summary>\n"
            f"<p style='font-size: 0.6rem; text-align: right; padding-bottom: -1em; margin-bottom: 0;'>"
            f"▚ type: {type(self).__name__}</p>"
            + "<ul style='padding-top: -1rem; margin-top: -1em; margin-bottom: 0.4rem;'>\n"
        )

        body = ""
        for key, value in self.items():
            if hasattr(value, "_repr_html_"):
                vrprs = value._repr_html_()
            else:
                vrprs = repr(value)

            body += f"<li><b>{key}</b>: {vrprs}</li>\n"

        tail = "</ul>\n</details>\n"

        return head + body + tail

    def _foamDictionary_del_value(self, entry) -> None:
        command = [
            "foamDictionary",
            str(self.path),
            "-entry",
            entry,
            "-remove",
            "-disableFunctionEntries",
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode != 0:
            raise ValueError(" ".join(command) + "\n\n" + value.stderr.strip())

    def _foamDictionary_get_value(self, entry) -> str:
        command = [
            "foamDictionary",
            str(self.path),
            "-entry",
            entry,
            "-value",
            "-disableFunctionEntries",
        ]
        value = run(command, cwd=self.path.parent)

        if value.returncode != 0:
            raise ValueError(" ".join(command) + "\n\n" + value.stderr.strip())

        return value.stdout.strip()

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

    def _foamDictionary_set_value(self, entry, value) -> None:
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
    Class for OpenFOAM files that stores directories.
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
    def internalField(self) -> OpenFoam_Dict | str:
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
            + "<summary style='font-size: 1.0rem; border-bottom: 1px solid purple; cursor: pointer;'>"
            + f"<b>{self.path.name}</b>"
            + "</summary>\n"
            + f"<p style='font-size: 0.6rem; text-align: right; padding-bottom: -1em; margin-bottom: 0;'>▚ type: {type(self).__name__}</p>"
            + "<ul style='padding-top: -1rem; margin-top: -1em; margin-bottom: 0.4rem;'>"
            + "\n".join([f"<li>{f.name}</li>\n" for f in self._files])
            + "\n</ul>\n"
            + "</details>\n"
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
            "<summary style='font-size: 1.0rem; border-bottom: none; cursor: pointer;'>"
            f"<em>{self.path.name}</em></summary>\n"
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

    def _blockMesh(self, verbose: bool = False):
        command = ["blockMesh"]

        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(
                " ".join(command) + "\n\n" + value.stdout.strip() + "\n\n" + value.stderr.strip()
            )

        if verbose:
            print("blockMesh finished successfully!")

    def _setFields(self, verbose: bool = False):
        command = ["setFields"]

        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(
                " ".join(command) + "\n\n" + value.stdout.strip() + "\n\n" + value.stderr.strip()
            )

        if verbose:
            print("setFields finished successfully!")

    def _runCase(self, verbose: bool = False):
        application = self.system.controlDict["application"]
        command = [application]

        value = run_solver(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        if verbose:
            print(f"{application} finished successfully!")

    def _foamListTimes(self):
        command = ["foamListTimes", "-withZero"]
        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        return value.stdout.strip().splitlines()

    def _foamListTimes_remove(self, verbose: bool = False):
        command = ["foamListTimes", "-rm"]
        value = run(command, cwd=self.path)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        if verbose:
            print(" ".join(command) + " finished successfully!")

    def export_to_xarray(self, ignore_initial_time: bool = True):
        """
        Export 1D result as a single xarray dataset.
        Requires xarray and pyvista.
        """

        path_to_nc = self.path / "postProcessing/espuma_as_netcdf"
        path_to_nc.mkdir(exist_ok=True)
        nc_file = path_to_nc / "results.nc"

        if nc_file.exists():
            return xr.open_dataset(nc_file, engine="netcdf4")

        ## Read each time folder in Foam results
        reader = self.get_vtk_reader()
        stacked: dict[str, pv.PolyData] = {}

        ts = slice(1, None) if ignore_initial_time else slice(None)

        for t in reader.time_values[ts]:
            reader.set_active_time_value(t)
            mesh = reader.read()  # <- Read the data
            internalMesh = mesh["internalMesh"]

            (xi, yi, zi, xf, yf, zf) = internalMesh.bounds

            initial_point = [xi, yi, zi]
            end_point = [xi, yi, zf]

            line_probe = internalMesh.sample_over_line(initial_point, end_point)
            stacked[f"{t:.2f}"] = line_probe

        ## Flatten vector data to separate 1D arrays
        expanded: dict[str, dict[str, np.ndarray]] = {}

        for t, x in stacked.items():
            expanded[t] = {}

            for name in x.array_names:
                if "vtk" not in name:
                    if len(x[name].shape) > 1:
                        for j in range(x[name].shape[1]):
                            expanded[t][name + "_" + str(j)] = x[name][:, j]
                    else:
                        expanded[t][name] = x[name]

        ## Convert to bare np and stack results as (time, depth)
        to_stack = []

        for x in expanded.values():
            to_stack.append(np.stack([v for v in x.values()], axis=-1))

        complete = np.stack(to_stack, axis=-1)

        # Metadata
        times = [float(t) for t in expanded.keys()]
        for x in expanded.values():
            variables = x.keys()
            distance = x["Distance"]
            break

        ## Assemble xarrays
        xars = {}

        for i, variable in enumerate(variables):
            a = complete[:, i, :]
            xars[variable] = xr.DataArray(
                a,
                dims=("depth", "time"),
                coords={"depth": distance, "time": times},
            )

        ## Combine into single dataset and save
        xdset = xr.Dataset(xars)
        xdset.to_netcdf(nc_file)

        return xdset

    @classmethod
    def clone_from_template(
        cls,
        template: Case_Directory,
        path: str | Path,
        overwrite: bool = False,
    ):
        if not isinstance(template, Case_Directory):
            raise TypeError(f"{template} must be a espuma.Case_Directory object")

        path = Path(path)

        if path.exists():
            if not overwrite:
                raise OSError(f"{path} already exists.\nMaybe you want to set overwrite=True?")

            if path.is_dir():
                rmtree(path)

            elif path.is_file():
                path.unlink()

        cls._foamCloneCase(template.path, path)

        return Case_Directory(path)

    @classmethod
    def _foamCloneCase(
        cls,
        source_case: str | Path,
        target_case: str | Path,
        verbose: bool = False,
    ):
        command = ["foamCloneCase", f'"{str(source_case)}"', '"{str(target_case)}"']
        value = run(command)

        if value.returncode != 0:
            raise OSError(" ".join(command) + "\n\n" + value.stderr.strip())

        if verbose:
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
        os.environ["ESPUMA_SCRIPTS"] = str((Path(__file__).parent / "scripts").absolute())

    else:
        warnings.warn("boundaryProbe parsing script not supported")
