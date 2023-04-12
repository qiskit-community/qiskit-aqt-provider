# This code is part of Qiskit.
#
# (C) Copyright IBM 2018.
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
copyright = "2021, Qiskit and AQT development teams"
author = "Qiskit and AQT development teams"

# The short X.Y version
version = "0.5.0"
# The full version, including alpha/beta/rc tags
release = "0.5.0"

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx.ext.extlinks",
    "jupyter_sphinx",
]
templates_path = ["_templates"]
html_static_path = ["_static"]
html_css_files = []

autosummary_generate = True
autosummary_generate_overwrite = False
autoclass_content = "both"

numfig = True

numfig_format = {"table": "Table %s"}
language = "en"

exclude_patterns = ["_build", "**.ipynb_checkpoints"]

pygments_style = "colorful"

add_module_names = False

modindex_common_prefix = ["qiskit_aqt."]

html_theme = "qiskit_sphinx_theme"
html_last_updated_fmt = "%Y/%m/%d"
html_theme_options = {
    "logo_only": True,
    "display_version": True,
    "prev_next_buttons_location": "bottom",
    "style_external_links": True,
}
