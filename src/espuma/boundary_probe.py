import xarray as xr
import numpy as np
from dataclasses import dataclass

import csv
from itertools import chain
from io import StringIO

from . import Case_Directory
from .base import Dict_File


@dataclass(slots=True, frozen=True)
class Point:
    x: float
    y: float
    z: float


class Boundary_Probe:
    def __init__(
        self,
        of_case: Case_Directory,
        probe_dict: Dict_File,
        parser_kwargs: dict | None = None,
    ):
        ## Generate organized files
        if parser_kwargs is None:
            parser_kwargs = {}

        self._boundaryProbes_to_txt(of_case, **parser_kwargs)

        processed_probes_path = of_case.path / "postProcessing/espuma_BoundaryProbes/"
        self.path_data = list(processed_probes_path.glob("points_*"))
        self.path_time = processed_probes_path / "time.txt"
        self.path_xyz = processed_probes_path / "xyz.txt"
        self.path_field_names = processed_probes_path / "fields.txt"

        self._id = str(processed_probes_path.relative_to(of_case.path))

        # TODO: Add functionality for CSV and VTK
        self._format = probe_dict["setFormat"].strip()

        if self._format != "csv":
            raise NotImplementedError(
                f"Only csv format is currently supported. Got {self._format}"
            )

        self._fields_expression = probe_dict["fields"].strip()

    @property
    def field_names(self) -> list[str]:
        return list(chain.from_iterable(self._field_names))

    @property
    def _field_names(self) -> list[list[str]]:
        with open(self.path_field_names) as f:
            names = f.readlines()

        return [name.strip().split() for name in names]

    @property
    def _n_fields(self) -> list[int]:
        return [len(_field_name) for _field_name in self._field_names]

    @property
    def n_fields(self) -> int:
        return sum(self._n_fields)

    @property
    def probe_points(self):
        with open(self.path_xyz) as f:
            xyz = f.readlines()
            xyz = [list(map(float, line.split())) for line in xyz]

        return [Point(*p) for p in xyz]

    @property
    def n_probes(self):
        return len(self.probe_points)

    @property
    def times(self):
        return np.loadtxt(self.path_time)

    @property
    def array_data(self):
        data = dict()

        for file_data, field_names, stride in zip(
            self.path_data, self._field_names, self._n_fields
        ):
            full_data = np.loadtxt(file_data).T

            for i, field in enumerate(field_names):
                data[field] = xr.DataArray(
                    full_data[i::stride] if stride > 1 else [full_data],
                    dims=("probes", "time"),
                    coords={"probes": self.probe_points, "time": self.times},
                )

        return xr.Dataset(
            data, coords={"time": self.times, "probes": self.probe_points}
        )

    def _repr_html_(self):
        return (
            f"<b>{self.__repr__()}</b><br>"
            "<dl>\n"
            + "<dt><i>Fields:</i></dt>\n"
            + "<dd>"
            + ", ".join(self.field_names)
            + "</dd>\n"
            + "<dt><i>Probes:</i></dt>\n"
            + "<dd>"
            + ", ".join([str(p) for p in self.probe_points])
            + "</dd>\n"
            + f"<dt><i>Times:</i></dt>\n<dd>From {self.times[0]} to {self.times[-1]} in {len(self.times)} steps</dd>\n</dl>"
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._id})"

    def _boundaryProbes_to_txt(self, of_case: Case_Directory, **parser_kwargs):
        """
        Parse the probe data into single files. The following files are created:
                - time.txt
                - xyz.txt
                - data.txt
                - fields.txt

        Parameters
        ----------
        None

        Returns
        -------
        None

        """

        bprbs = of_case.path / "postProcessing/boundaryProbes"
        outbprs = of_case.path / "postProcessing/espuma_BoundaryProbes"

        if not parser_kwargs.get("rebuild", False) and outbprs.exists():
            print(f"{outbprs.name} already exists :)")
            return None

        if not bprbs.exists():
            raise FileNotFoundError(f"{bprbs.name} does not exist. Nothing to parse")

        if parser_kwargs.get("rebuild", False) or not outbprs.exists():
            if not outbprs.exists():
                outbprs.mkdir()

            ## Write times file
            times = [x for x in bprbs.iterdir() if x.is_dir()]
            times.sort(key=lambda x: float(x.name))

            with open(outbprs / "time.txt", "w") as out:
                out.writelines([str(t.name) + "\n" for t in times])

            ## Write probe locations
            sample = next(times[1].iterdir())  ## Grab a sample

            with open(outbprs / "xyz.txt", "w") as out:
                with open(sample) as f:
                    f.readline()  ## Skip header

                    for line in f:
                        coords = line.split(",")[:3]
                        out.write(" ".join(coords) + "\n")

            ## Write the fields name file
            with open(outbprs / "fields.txt", "w") as out:
                for point_file in times[1].iterdir():
                    with open(point_file) as f:
                        out.write(" ".join(f.readline().split(",")[3:]))

            ## Write the data file
            vars = [f.name for f in times[1].iterdir()]
            for var in vars:
                with StringIO() as buffer:
                    for time in times:
                        with open(time / var) as f:
                            r = csv.reader(f, delimiter=",")
                            r = (
                                y[3:] for y in list(r)[1:]
                            )  ## Gets rid of first three columns
                            r = chain.from_iterable(r)  ## Make single row (drop first)
                            r = " ".join(r).replace(
                                "  ", " "
                            )  ## Format single space separation
                            buffer.write(r + "\n")

                    with open(outbprs / var, "w") as f:
                        f.write(buffer.getvalue())

        else:
            print("postProcessing/espuma_BoundaryProbes already exists.")


def main():
    pass


if __name__ == "__main__":
    main()
