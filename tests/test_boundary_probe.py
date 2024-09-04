from espuma import Case_Directory, Boundary_Probe

TEMPLATE = "./templates/breakthrough/"
PATH = "./tests/pytest_breakthrough_base"


def test_initialize():
    global of_case

    of_tpl = Case_Directory(TEMPLATE)
    of_case = Case_Directory.clone_from_template(of_tpl, PATH, overwrite=True)
    # of_case = Case_Directory(PATH)

    of_case.system.controlDict["writeControl"] = "runTime"
    of_case.system.controlDict["writeInterval"] = "0.01"

    of_case._blockMesh()

    boundary_probe_dict = of_case.system.boundaryProbes
    assert boundary_probe_dict["interpolationScheme"] == "cellPatchConstrained"
    assert boundary_probe_dict["writeControl"] == "runTime"

    assert boundary_probe_dict["setFormat"] == "raw"

    boundary_probe_dict["setFormat"] = "csv"
    assert boundary_probe_dict["setFormat"] == "csv"

    boundary_probe_dict["fields"] = """("T" "U")"""
    boundary_probe_dict["patches"] = """("bottom" "top")"""

    assert boundary_probe_dict["writeControl"] == "runTime"
    boundary_probe_dict["writeInterval"] = "0.001"

    of_case._runCase()


def test_boundary_probe():
    probe = Boundary_Probe(of_case, probe_dict=of_case.system.boundaryProbes)

    assert probe.path_time.samefile(
        of_case.path / "postProcessing/espuma_BoundaryProbes/time.txt"
    )

    assert probe.path_xyz.samefile(
        of_case.path / "postProcessing/espuma_BoundaryProbes/xyz.txt"
    )

    assert probe.path_field_names.samefile(
        of_case.path / "postProcessing/espuma_BoundaryProbes/fields.txt"
    )

    assert probe.n_fields == 4
    assert "T" in probe.field_names
    assert "U_0" in probe.field_names
    assert "U_1" in probe.field_names
    assert "U_2" in probe.field_names
