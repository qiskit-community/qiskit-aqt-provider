# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import os
import setuptools

requirements = [
    "requests>=2.19",
    "qiskit-terra>=0.17.0",
]

PACKAGES = setuptools.find_packages(exclude=["test*"])

version_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "qiskit_aqt_provider", "VERSION.txt")
)

with open(version_path, "r") as fd:
    version = fd.read().rstrip()

README_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), "README.md")
with open(README_PATH) as readme_file:
    README = readme_file.read()

setuptools.setup(
    name="qiskit-aqt-provider",
    version=version,
    packages=PACKAGES,
    description="Qiskit provider for AQT backends",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/Qiskit-Partners/qiskit-aqt-provider",
    author="Qiskit Development Team",
    author_email="qiskit@qiskit.org",
    license="Apache 2.0",
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering",
    ],
    keywords="qiskit sdk quantum",
    install_requires=requirements,
    include_package_data=True,
    python_requires=">=3.6",
    project_urls={
        "Bug Tracker": "https://github.com/Qiskit-Partners/qiskit-aqt-provider/issues",
        "Source Code": "https://github.com/Qiskit-Partners/qiskit-aqt-provider",
        "Documentation": "https://qiskit.org/documentation/partners/aqt/",
    },
    zip_safe=False,
)
