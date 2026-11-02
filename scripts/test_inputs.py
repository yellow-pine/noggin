"""inputs.py: the repo files a file is made from, its imports followed through (ast)."""

from scripts.inputs import inputs


def test_inputs_follow_the_imports_through_the_repo():
    assert {"model/fits.py", "model/linkage.py", "model/printed/lid.py"} <= inputs("model/ours.py")
    assert "reactions/director.py" in inputs("mech/test_mech.py")  # through noggin/service.py
    assert not any(f.startswith(".venv") for f in inputs("model/ours.py"))  # numpy, cadquery: not the repo's
    assert "model/__init__.py" not in inputs("model/ours.py")  # empty: no input
