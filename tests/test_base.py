from espuma.base import Case_Directory

PATH = "/home/edsaa/foam/cavity"
of_case = Case_Directory(PATH)


def test_case_directory():
    assert str(of_case) == PATH
    assert str(of_case.zero) == f"{PATH}/0"
    assert str(of_case.system) == f"{PATH}/system"


def test_zero_directory():

    assert getattr(of_case.zero, "p")
    assert getattr(of_case.zero, "U")

    assert f"{PATH}/0/p" in of_case.zero.files
    assert f"{PATH}/0/U" in of_case.zero.files
    assert len(of_case.zero.files) == 2


def test_scalar_field():
    p = of_case.zero.p

    assert str(p) == f"{PATH}/0/p"
    assert p["FoamFile.class"] == "volScalarField"

    assert str(p.dimensions) == "[0 2 -2 0 0 0 0]"
    assert str(p.internalField) == "uniform 0"
    assert all(
        i in p.boundaryField.keys()
        for i in ("fixedWalls", "movingWall", "frontAndBack")
    )
    assert p.boundaryField["fixedWalls"]["type"] == "zeroGradient"
    assert p.boundaryField["fixedWalls.type"] == "zeroGradient"


def test_vector_field():
    U = of_case.zero.U

    assert str(U) == f"{PATH}/0/U"
    assert U["FoamFile.class"] == "volVectorField"

    assert str(U.dimensions) == "[0 1 -1 0 0 0 0]"
    assert str(U.internalField) == "uniform ( 0 0 0 )"
    assert all(
        i in U.boundaryField.keys()
        for i in ("fixedWalls", "movingWall", "frontAndBack")
    )
    assert U.boundaryField["fixedWalls"]["type"] == "noSlip"
    assert U.boundaryField["fixedWalls.type"] == "noSlip"


def test_constant_directory():
    constant = of_case.constant
    assert str(constant) == f"{PATH}/constant"

    assert str(constant.transportProperties) == f"{PATH}/constant/transportProperties"
    
    assert constant.transportProperties["FoamFile.class"] == "dictionary"
    assert constant.transportProperties["nu"] == "[ 0 2 -1 0 0 0 0 ] 0.01"

def test_system_directory():
    system = of_case.system

    assert str(system.controlDict) == f"{PATH}/system/controlDict"
    assert system.controlDict["FoamFile.class"] == "dictionary"
    assert system.controlDict["application"] == "icoFoam"
    assert system.controlDict["deltaT"] == "0.005"

    assert str(system.fvSolution) == f"{PATH}/system/fvSolution"
    assert system.fvSolution["PISO"]["nCorrectors"] == "2"


def test_getters():
    fv_schemes = of_case.system.fvSchemes

    assert str(fv_schemes) == f"{PATH}/system/fvSchemes"
