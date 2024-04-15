# This code is part of Qiskit.
#
# (C) Copyright IBM 2018, Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Sphinx documentation builder."""

project = "Qiskit AQT Provider"
copyright = "2023, Qiskit and AQT development teams"
author = "Qiskit and AQT development teams"

# The short X.Y version
version = "1.4.0"
# The full version, including alpha/beta/rc tags
release = "1.4.0"

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.autodoc_pydantic",
    "jupyter_sphinx",
    "qiskit_sphinx_theme",
]

# --------------------
# Theme
# --------------------

html_theme = "qiskit-ecosystem"
pygments_style = "emacs"
html_title = f"{project} {release}"

# --------------------
# General options
# --------------------

language = "en"
exclude_patterns = ["_build", "**.ipynb_checkpoints"]

# check that all links are valid, with some exceptions
nitpicky = True
nitpick_ignore = [
    ("py:class", "pydantic.main.BaseModel"),
    ("py:class", "Backend"),
    ("py:class", "Target"),
    ("py:exc", "QiskitBackendNotFoundError"),
]
nitpick_ignore_regex = [
    ("py:class", r"qiskit_aqt_provider\.api_models_generated.*"),
    ("py:class", r"typing_extensions.*"),
]

# show fully qualified names
add_module_names = True

# --------------------
# Autodoc options
# --------------------

# separate the class docstring from the __init__ signature.
autodoc_class_signature = "separated"

# do not list the Pydantic validators in the field documentation.
autodoc_pydantic_field_list_validators = False

# ------------------------------
# Intersphinx configuration
# ------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "qiskit": ("https://docs.quantum.ibm.com/api/qiskit/", None),
}
