# Changelog

## Unreleased

* Add an experimental QIR to AQT API converter (#162)

## qiskit-aqt-provider v1.5.0

* Docs: add examples on setting run options in primitives (#156)
* Provider: remove `ProviderV1` inheritance (#160)

## qiskit-aqt-provider v1.4.0

* Only support Qiskit >= 1.0 (#141)
* Transpiler: always decompose wrapped-angle RXX gates (#145, #146)
* Docs: recommend using `optimization_level 3` in the Qiskit transpiler (#146)

## qiskit-aqt-provider v1.3.0

* Point Qiskit docs links to docs.quantum.ibm.com (#135)
* Remove references to the deprecated function `qiskit.execute` (#136)
* Pin Qiskit dependency strictly below 1.0 (#137)
* Remove the Grover 3-SAT example (#137)

## qiskit-aqt-provider v1.2.0

* Add support for Python 3.12 (#79)
* Remove support for Python 3.8 (#79)
* Improve math typesetting in user guide (#124)
* Fix transpilation issue on Windows (issue #121) (#123)

## qiskit-aqt-provider v1.1.0

* Update to `pydantic` v2 (#66)
* Update API specification to track the production server (#66)

## qiskit-aqt-provider v1.0.0

* Set minimal required `qiskit` version to 0.45.0 (#108)
* Use `qiskit-algorithms` package instead of deprecated `qiskit.algorithms` in examples (#110)
* Use arnica.aqt.eu instead of arnica-stage.aqt.eu as default portal (#111)

## qiskit-aqt-provider v0.19.0

* Interpret string filters in `AQTProvider.get_backend()` as exact matches, not patterns (#90)
* Fix incorrect handling of qubit/clbit permutations by offline simulators (#93)
* Depend on [qiskit](https://pypi.org/project/qiskit/) instead of [qiskit-terra](https://pypi.org/project/qiskit-terra) (#95)
* Remove use of deprecated `Bit.index` and `Bit.register` (#99)
* Use [`ruff format`](https://docs.astral.sh/ruff/formatter/) instead of `black` (#101)

## qiskit-aqt-provider v0.18.0

* Check that the circuits submitted to the offline simulators can be converted to the AQT API (#68)
* Update the user guide and improve the API reference consistency (#72, #75)
* Add quickstart examples for the Qiskit.org homepage (#73)
* Add persistence mechanism for `AQTJob` instances (#77)
* Rename `OfflineSimulatorResource.noisy` to `OfflineSimulatorResource.with_noise_model` (#77)

## qiskit-aqt-provider v0.17.0

* Merge community and AQT versions (#61)

## qiskit-aqt-provider v0.16.0

* Make the access token optional (alpine-quantum-technologies/qiskit-aqt-provider-rc#80)
* Add simple QAOA examples (alpine-quantum-technologies/qiskit-aqt-provider-rc#81)

## qiskit-aqt-provider v0.15.0

* Set default portal url to `https://arnica-stage.aqt.eu` (alpine-quantum-technologies/qiskit-aqt-provider-rc#79)

## qiskit-aqt-provider v0.14.0

* Add `AQTEstimator`, a specialized implementation of the `Estimator` primitive (alpine-quantum-technologies/qiskit-aqt-provider-rc#71)
* Add simple VQE example (alpine-quantum-technologies/qiskit-aqt-provider-rc#71)
* Update pinned dependencies (alpine-quantum-technologies/qiskit-aqt-provider-rc#72)
* Add `offline_simulator_noise` resource with basic noise model (alpine-quantum-technologies/qiskit-aqt-provider-rc#73)

## qiskit-aqt-provider v0.13.0

* Always raise `TranspilerError` on errors in the custom transpilation passes (alpine-quantum-technologies/qiskit-aqt-provider-rc#57)
* Add `AQTSampler`, a specialized implementation of the `Sampler` primitive (alpine-quantum-technologies/qiskit-aqt-provider-rc#60)
* Auto-generate and use Pydantic models for the API requests payloads (alpine-quantum-technologies/qiskit-aqt-provider-rc#62)
* Use server-side multi-circuits jobs API (alpine-quantum-technologies/qiskit-aqt-provider-rc#63)
* Add job completion progress bar (alpine-quantum-technologies/qiskit-aqt-provider-rc#63)
* Allow overriding any backend option in `AQTResource.run` (alpine-quantum-technologies/qiskit-aqt-provider-rc#64)
* Only return raw memory data when the `memory` option is set (alpine-quantum-technologies/qiskit-aqt-provider-rc#64)
* Implement the `ProviderV1` interface for `AQTProvider` (alpine-quantum-technologies/qiskit-aqt-provider-rc#65)
* Set User-Agent with package and platform information for HTTP requests (alpine-quantum-technologies/qiskit-aqt-provider-rc#65)
* Add py.typed marker file (alpine-quantum-technologies/qiskit-aqt-provider-rc#66)
* Rename package to `qiskit-aqt-provider-rc` (alpine-quantum-technologies/qiskit-aqt-provider-rc#67)

## qiskit-aqt-provider v0.12.0

* Use `ruff` instead of `pylint` as linter (alpine-quantum-technologies/qiskit-aqt-provider-rc#51)
* Publish release artifacts to PyPI (alpine-quantum-technologies/qiskit-aqt-provider-rc#55)

## qiskit-aqt-provider v0.11.0

* Expose the result polling period and timeout as backend options (alpine-quantum-technologies/qiskit-aqt-provider-rc#46)
* Support `qiskit.result.Result.get_memory()` to retrieve the raw results bitstrings (alpine-quantum-technologies/qiskit-aqt-provider-rc#48)

## qiskit-aqt-provider v0.10.0

* Add a Grover-based 3-SAT solver example (alpine-quantum-technologies/qiskit-aqt-provider-rc#31)
* Wrap `Rxx` angles to [0, π/2] instead of [-π/2, π/2] (alpine-quantum-technologies/qiskit-aqt-provider-rc#37)
* Wrap single-qubit rotation angles to [0, π] instead of [-π, π]  (alpine-quantum-technologies/qiskit-aqt-provider-rc#39)
* Remove provider for legacy API (alpine-quantum-technologies/qiskit-aqt-provider-rc#40)
* Automatically load environment variables from `.env` files (alpine-quantum-technologies/qiskit-aqt-provider-rc#42)

## qiskit-aqt-provider v0.9.0

* Fix and improve error handling from individual circuits (alpine-quantum-technologies/qiskit-aqt-provider-rc#24)
* Run the examples in the continuous integration pipeline (alpine-quantum-technologies/qiskit-aqt-provider-rc#26)
* Automatically create a Github release when a version tag is pushed (alpine-quantum-technologies/qiskit-aqt-provider-rc#28)
* Add `number_of_qubits` to the `quantum_circuit` job payload (alpine-quantum-technologies/qiskit-aqt-provider-rc#29)
* Fix the substitution circuit for wrapping the `Rxx` angles (alpine-quantum-technologies/qiskit-aqt-provider-rc#30)
* Connect to the internal Arnica on port 80 by default (alpine-quantum-technologies/qiskit-aqt-provider-rc#33)

## qiskit-aqt-provider v0.8.1

* Relax the Python version requirement (alpine-quantum-technologies/qiskit-aqt-provider-rc#23)

## qiskit-aqt-provider v0.8.0

* Allow the transpiler to decompose any series of single-qubit rotations as ZRZ (alpine-quantum-technologies/qiskit-aqt-provider-rc#13)
* Wrap single-qubit rotation angles to [-π, π] (alpine-quantum-technologies/qiskit-aqt-provider-rc#13)
* Add `offline_simulator_no_noise` resource (based on Qiskit-Aer simulator) to all workspaces (alpine-quantum-technologies/qiskit-aqt-provider-rc#16)
* Add simple execution tests (alpine-quantum-technologies/qiskit-aqt-provider-rc#16)
* Use native support for arbitrary-angle RXX gates (alpine-quantum-technologies/qiskit-aqt-provider-rc#19)
* Stricter validation of measurement operations (alpine-quantum-technologies/qiskit-aqt-provider-rc#19)
* Allow executing circuits with only measurement operations (alpine-quantum-technologies/qiskit-aqt-provider-rc#19)

## qiskit-aqt-provider v0.7.0

* Fix quantum/classical registers mapping (alpine-quantum-technologies/qiskit-aqt-provider-rc#10)
* Allow jobs with multiple circuits (alpine-quantum-technologies/qiskit-aqt-provider-rc#10)
* Use `poetry` for project setup (alpine-quantum-technologies/qiskit-aqt-provider-rc#7)

## qiskit-aqt-provider v0.6.1

* Fixes installation on windows (alpine-quantum-technologies/qiskit-aqt-provider-rc#8)

## qiskit-aqt-provider v0.6.0

* Initial support for the Arnica API (alpine-quantum-technologies/qiskit-aqt-provider-rc#4)
* Setup Mypy typechecker (alpine-quantum-technologies/qiskit-aqt-provider-rc#3)
