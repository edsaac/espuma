import subprocess
from pathlib import Path
import shutil
import os

import pyvista as pv
import numpy as np
import xarray as xr
from dataclasses import dataclass
from math import isclose

from io import StringIO
from datetime import datetime

import matplotlib.pyplot as plt
import matplotlib.colors as colors


@dataclass
class Base_OpenFOAM:
    path_case: str | Path

    def __post_init__(self) -> None:
        self.path_case = Path(self.path_case)

        ## Check if case need to be cloned or already exists
        if not self.path_case.exists():
            raise ValueError("`path_template` not a directory.")
        else:
            self.logger("<'.'> Case exists! No need to clone template.")

    def _repr_html_(self):
        html = (
            f"<h3>{self.__class__.__name__} object</h3>\n"
            f"<p><b>path_case:  </b>{str(self.path_case)}<br>"
            f"<b>path_template:  </b>{self.path_template}</p>\n"
        )
        
        return html


    def get_value_from_foamDictionary(self, location: str, entry: str, is_vector: bool = False):
        command = ["foamDictionary", location, "-entry", entry, "-value"]

        value = subprocess.run(
            command,
            cwd=self.path_case,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if value.returncode == 0:

            if is_vector:
                return value.stdout.split("(")[-1].replace(")", "").strip().split()
            else:
                return value.stdout.split()[-1].replace(";", "")

        else:
            raise ValueError(" ".join(command) + " get returned with error")

    def set_value_in_foamDictionary(
        self, location: str, entry: str, value: float | str
    ):
        command = ["foamDictionary", location, "-entry", entry, "-set", value]

        completed_process = subprocess.run(
            command,
            cwd=self.path_case,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if completed_process.returncode > 0:
            raise ValueError(" ".join(command) + " set returned with error")

    def remove_entry_in_foamDictionary(self, location: str, entry: str):
        command = ["foamDictionary", location, "-entry", entry, "-remove"]

        completed_process = subprocess.run(
            command,
            cwd=self.path_case,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if completed_process.returncode > 0:
            raise ValueError(" ".join(command) + " remove returned with error")

    @property
    def solver(self):
        return self.get_value_from_foamDictionary(
            "system/controlDict", entry="application"
        )

    def clone_from_template(self):
        # print(self.path_template)
        subprocess.run(["mkdir", self.path_case])
        subprocess.run(
            [
                "cp",
                "-r",
                self.path_template / "0.000",
                self.path_template / "constant",
                self.path_template / "system",
                # self.path_template / "VTK",
                # self.path_template / "VTK_soilProperties",
                # self.path_template / "organizedData",
                self.path_case,
            ]
        )

    @property
    def latest_time(self) -> str:
        """
        Run `foamListTimes` to get the latest time in the simulation.

        Returns
        -------
        str
            Folder name with the latest time

        """

        command = ["foamListTimes", "-latestTime"]

        foamListTimes = subprocess.run(
            command,
            cwd=self.path_case,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if foamListTimes.returncode == 0:
            if not foamListTimes.stdout:
                return "0.000"
            else:
                return foamListTimes.stdout.replace("\n", "")

        else:
            self.logger(" ".join(command) + " returned with error")

    @property
    def list_times(self):
        """ 
        Run `foamListTimes` to get the latest time in the simulation.

        Returns
        -------
        str
            Folder name with the latest time
        """

        command = ["foamListTimes"]

        foamListTimes = subprocess.run(
            command,
            cwd=self.path_case,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        if foamListTimes.returncode == 0:
            if not foamListTimes.stdout:
                return "0.000"
            else:
                return foamListTimes.stdout.splitlines()

        else:
            self.logger(" ".join(command) + " returned with error")


    def set_endtime(self, time_minutes: int) -> None:
        time_sec = str(int(time_minutes * 60))  # OpenFOAM expects seconds

        self.set_value_in_foamDictionary("system/controlDict", "endTime", time_sec)

    def set_writeInterval(self, time_minutes: int) -> None:
        # OpenFOAM expects values in seconds
        time_sec = str(int(time_minutes * 60))  # OpenFOAM expects seconds

        self.set_value_in_foamDictionary(
            "system/controlDict", "writeInterval", time_sec
        )

    def set_convergeThreshold(self, value: float):
        """
        Refers to the converge threshold used in the Picard iterations of the Richards'
        solver.
        """
        if value <= 0:
            raise ValueError("convergeThreshold must be positive")

        self.set_value_in_foamDictionary(
            "system/fvSolution", "timeStepping.convergeThreshold", f"{value:.6f}"
        )

    def set_boundary_fixedValue(
        self, value: float = -1e-6, patch: str = "top", field: str = "h"
    ):
        """
        Run `foamDictionary` to set the a boundary condition to fixedValue
        of the latest simulated time

        Parameters
        ----------
        value: float
            Value of the Dirichlet boundary condition

        patch: str
            Name of the patch to modify

        field: str
            Name of the field to modify

        Returns
        -------
        None

        Notes
        ------
        This is the code run:
        ```
        $ foamDictionary $LATEST_TIME/h -entry boundaryField.top.type \
            -set "fixedValue"
        $ foamDictionary $LATEST_TIME/h -entry boundaryField.top.value \
            -set "uniform 0.06"
        $ foamDictionary $LATEST_TIME/h -entry boundaryField.top.gradient \
            -remove
        ```
        """

        t = self.latest_time
        dict_loc = f"{t}/{field}"
        boundary = f"boundaryField.{patch}"

        self.set_value_in_foamDictionary(dict_loc, boundary, f"{{type  fixedValue; value  uniform {value:.4E}; }}")
        # self.set_value_in_foamDictionary(
        #     dict_loc, f"{boundary}.value", f"uniform {value:.4E}"
        # )
        # self.remove_entry_in_foamDictionary(dict_loc, f"{boundary}.gradient")

    def set_boundary_fixedGradient(
        self, value: float = -1.0, patch: str = "top", field: str = "h"
    ):
        """
        Run `foamDictionary` to set the a boundary condition to fixedGradient
        of the latest simulated time

        Parameters
        ----------
        value: float
            Value of the Dirichlet boundary condition

        patch: str
            Name of the patch to modify

        field: str
            Name of the field to modify

        Returns
        -------
        None

        Notes
        -----
        ```
        $ foamDictionary $LATEST_TIME/h -entry boundaryField.top.type \
            -set "fixedGradient"
        $ foamDictionary $LATEST_TIME/h -entry boundaryField.top.gradient \
            -set "uniform -1"
        $ foamDictionary $LATEST_TIME/h -entry boundaryField.top.value \
            -remove
        ```
        """

        t = self.latest_time
        dict_loc = f"{t}/{field}"
        boundary = f"boundaryField.{patch}"

        self.set_value_in_foamDictionary(dict_loc, boundary, f"{{type  fixedGradient; gradient uniform {value}; }}")

        # self.set_value_in_foamDictionary(dict_loc, f"{boundary}.type", "fixedGradient")
        # self.set_value_in_foamDictionary(
        #     dict_loc, f"{boundary}.gradient", f"uniform {value}"
        # )
        # self.remove_entry_in_foamDictionary(dict_loc, f"{boundary}.value")

    def cleanup_last_timestep(self):
        """
        Remove ddt and _0 files generated by Crank-Nicholson timesteper.
        Remove also the "uniform" folder containing time metadata
        """
        path_latest_time = self.path_case / self.latest_time

        # ddts from CrankNicholson
        for f in path_latest_time.glob("ddt*"):
            f.unlink()

        for f in path_latest_time.glob("*_0"):
            f.unlink()

        if (path_latest_time / "uniform/time").exists():
            shutil.rmtree(path_latest_time / "uniform")

    def cleanup_all_timesteps(self):
        """
        Remove ddt and _0 files from all folders.
        This is done so foamToVTK does not freak out.
        """
        for f in self.path_case.glob("**/ddt*"):
            f.unlink()

        for f in self.path_case.glob("**/*_0"):
            if (
                f.name != "K_0"
            ):  # Exception for the clean saturated hydraulic conductivity
                f.unlink()

        for f in self.path_case.glob("**/uniform"):
            shutil.rmtree(f)

    def run_solver(self):
        """
        Executes the solver

        Parameters
        ----------
        solver: str
            Name of the solver

        Returns
        -------
        None
        """
        if self.solver not in ["unsatFoam", "unsatNutrientCycle"]:
            raise ValueError("Solver not valid")
        else:
            openfoam_run = subprocess.run(
                [self.solver], stdout=subprocess.DEVNULL, cwd=self.path_case
            )

        return openfoam_run.returncode

    def foam_to_vtk(self):
        """
        Export all timesteps to VTK and the soil parameters into a separate folder

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.cleanup_all_timesteps()

        path_soilParameters = Path("./constant/soilParameters/")
        # list_soilParameters = ["alpha", "K_0", "n_vangenucthen", "Sw_r", "Sw_s"]

        # for param in list_soilParameters:
        #     (path_soilParameters/param).unlink()

        subprocess.run("rm -rf VTK VTK_soilProperties".split(), cwd=self.path_case)
        subprocess.run(
            [
                "cp",
                path_soilParameters / "alpha",
                path_soilParameters / "K_0",
                path_soilParameters / "n_vangenucthen",
                path_soilParameters / "Sw_r",
                path_soilParameters / "Sw_s",
                "./0.000/",
            ],
            cwd=self.path_case,
        )

        subprocess.run(
            [
                "foamToVTK",
                "-fields",
                "(h alpha K_0 n_vangenucthen Sw_r Sw_s)",
                "-time",
                '"0"',
            ],
            cwd=self.path_case,
            stdout=subprocess.DEVNULL,
        )

        subprocess.run("mv VTK VTK_soilProperties".split(), cwd=self.path_case)
        subprocess.run(
            [
                "rm",
                "0.000/alpha",
                "0.000/K_0",
                "0.000/n_vangenucthen",
                "0.000/Sw_r",
                "0.000/Sw_s",
            ],
            cwd=self.path_case,
        )

        # Export relevant fields to VTK for test comparison
        # foamToVTK -fields "(XAR XN XDN XI XARp XNp XDNp DOC NH4 NO3 O2 tracer \
        #    BAP POCr Sw h porosity hydraulicCond U)"
        fields = ["Sw", "h", "porosity", "hydraulicCond", "U", "capillarity"]

        if self.solver == "unsatFoam":
            pass
        elif self.solver == "unsatNutrientCycle":
            fields += ["XAR", "XN", "XDN", "EPS", "XI"]  # Immobile
            fields += ["DOC", "O2", "NH4", "NO3", "tracer"]  # Dissolved
            fields += ["POCr", "BAP", "XARp", "XNp", "XDNp"]  # Particulates

        fields = f"({' '.join(fields)})"

        process = subprocess.run(
            [
                "foamToVTK",
                "-fields",
                fields,
                "-noZero",
            ],
            cwd=self.path_case,
            stdout=subprocess.DEVNULL,
        )

        if process.returncode > 0:
            raise ValueError("foamToVTK returned with error")
        
        # Initialize organizedData folder for plots and stuff
        organizedData_path = Path(self.path_case / "organizedData")
        if not organizedData_path.exists():
            os.makedirs(organizedData_path)
            self.logger("organizedData folder created")
        
        heatmaps_path = organizedData_path / "heatmaps"
        if not heatmaps_path.exists():
            os.makedirs(heatmaps_path)


    def boundaryProbes_to_txt(self):
        """
        Run pointFiles.sh on the case to parse the probe data into single files

        A symlink to pointFiles.sh is located in the ~/bin folder.

        Parameters
        ----------
        None

        Returns
        -------
        None
            The following files are created:
                - time.txt
                - xyz.txt
                - $field.xy
        """

        subprocess.call(
            ["pointFiles.sh", "./postProcessing/boundaryProbes"],
            cwd=self.path_case,
        )

    def process_boundaryProbes(self):
        """
        Read the processed boundaryProbes and parse them in xarrays

        """
        processed_probes_path = self.path_case / "organizedData/"
        files = processed_probes_path.glob("points_*")
        f_time = processed_probes_path / "time.txt"
        f_xyz = processed_probes_path / "xyz.txt"

        self.boundaryProbes = [boundaryProbe(f, f_time, f_xyz) for f in files]

    def plot_xarray(self):
        for bp in self.boundaryProbes:
            for k, v in bp.array_data.items():
                fig, ax = plt.subplots(figsize=[6, 5])
                v.plot.line(x="time", ax=ax, lw=1)

                plt.savefig(
                    self.path_case
                    / "organizedData/heatmaps"
                    / f"{self.path_case.name}_xarray_{k}.png",
                    dpi=300,
                )

    def read_as_xarray_dataset(self, fields:list[str]):
        """
        Export all VTK timesteps and fields to an xarray Dataset

        Returns
        -------
        xr.Dataset
            With depth and time as the dimensions and each parameter
        """
        
        ## Extract VTK result (this should be done with a probe but meh)
        all_vtk_paths = [self.path_vtk / f for f in getVTKList(self.path_vtk)]
        nTimes = len(all_vtk_paths)
        times = [
            float(t)
            for t in subprocess.check_output(
                "foamListTimes", cwd=self.path_case, text=True, encoding="utf-8"
            ).splitlines()
            if t[0:2].isnumeric()
        ]

        ## Use dimensions from the first VTK
        mesh = pv.read(all_vtk_paths[0])
        _ = pv.Line(a := [0, 0, mesh.bounds[5]], b := [0, 0, mesh.bounds[2]])

        sample = mesh.sample_over_line(a, b)
        nPoints = len(sample[fields[0]]) #<- One of the fields

        ## Initialize array to store data
        mapping = dict()

        for field in fields:
            
            ## A temp array
            results = np.zeros([nPoints, nTimes])

            ## Extract field for each vtk field
            for t, vtk in enumerate(all_vtk_paths):
                mesh = pv.read(vtk)
                sample = mesh.sample_over_line(a, b)
                results[:, t] = sample[field]

            mapping[field] = xr.DataArray(
                results, dims=("z", "t"), coords={"z": sample.points[:, 2], "t": times}
            )

        return xr.Dataset(mapping)


    def read_field_all_times(self, field: str):
        """
        Export all VTK timesteps to an xarray

        Parameters
        ----------
        field: str
            Name of the field to read

        Returns
        -------
        xr.Array
            With depth and time as the dimensions
        """

        ## Extract VTK result (this should be done with a probe but meh)
        all_vtk_paths = [self.path_vtk / f for f in getVTKList(self.path_vtk)]
        nTimes = len(all_vtk_paths)
        times = [
            float(t)
            for t in subprocess.check_output(
                "foamListTimes", cwd=self.path_case, text=True, encoding="utf-8"
            ).splitlines()
            if t[0:2].isnumeric()
        ]

        ## Use dimensions from the first VTK
        mesh = pv.read(all_vtk_paths[0])
        _ = pv.Line(a := [0, 0, mesh.bounds[5]], b := [0, 0, mesh.bounds[2]])

        sample = mesh.sample_over_line(a, b)
        nPoints = len(sample[field])

        ## Initialize array to store data
        results = np.zeros([nPoints, nTimes])

        ## Extract field for each vtk field
        for t, vtk in enumerate(all_vtk_paths):
            mesh = pv.read(vtk)
            sample = mesh.sample_over_line(a, b)
            results[:, t] = sample[field]

        data = xr.DataArray(
            results, dims=("z", "t"), coords={"z": sample.points[:, 2], "t": times}
        )

        return data

    def plot_field_over_time(self, field: str, pcolormesh_kwargs: dict, save_png: bool = False):
        """
        Generates a Depth-time heatmap plot of the field

        Parameters
        ----------
        field: str
            Name of the field to plot.

        Returns
        -------
        None
            It should save a plot in the organizedData folder of the case

        """

        scalar = self.read_field_all_times(field)

        igt = 0
        fig, (cax, ax) = plt.subplots(
            2, 1, figsize=[5, 5], gridspec_kw={"height_ratios": [0.2, 5]}, sharex=False
        )

        if pcolormesh_kwargs.get("LogNorm"):
            pcolormesh_kwargs["norm"] = colors.LogNorm(
                **pcolormesh_kwargs["LogNorm"]
            )

            del pcolormesh_kwargs["LogNorm"]

        img = ax.pcolormesh(
            scalar.t[igt:] / 86400, scalar.z, scalar[:, igt:], 
            **pcolormesh_kwargs
        )
        ax.spines.right.set_visible(False)
        ax.set_xlabel("Time $t$ [d]")
        ax.set_ylabel("Depth $z$ [m]")
        plt.colorbar(img, cax=cax, orientation="horizontal")
        cax.set_title(rf"{field} [units]")
        fig.tight_layout()

        if save_png:
            plt.savefig(
                self.path_case
                / "organizedData/heatmaps"
                / f"{self.path_case.name}_{field}.png",
                dpi=300,
            )
        
        else:
            return fig

    def logger(self, *msgs: str):
        
        if not self.write_to_log:
            return None

        for msg in msgs:
            self._log_buffer.write(msg)

        with open(self.path_case / f"{self.path_case.name}.log", "a") as f:
            f.write(self._log_buffer.getvalue())
            f.write("\n")

        self._log_buffer = StringIO()
