# Changelog

## Unreleased

* Add a Grover-based 3-SAT solver example #31
* Wrap `Rxx` angles to [0, π/2] instead of [-π/2, π/2] #37
* Wrap single-qubit rotation angles to [0, π] instead of [-π, π]  #39
* Remove provider for legacy API #40
* Automatically load environment variables from `.env` files #42

## qiskit-aqt-provider v0.9.0

* Fix and improve error handling from individual circuits #24
* Run the examples in the continuous integration pipeline #26
* Automatically create a Github release when a version tag is pushed #28
* Add `number_of_qubits` to the `quantum_circuit` job payload #29
* Fix the substitution circuit for wrapping the `Rxx` angles #30
* Connect to the internal Arnica on port 80 by default #33

## qiskit-aqt-provider v0.8.1

* Relax the Python version requirement #23

## qiskit-aqt-provider v0.8.0

* Allow the transpiler to decompose any series of single-qubit rotations as ZRZ #13
* Wrap single-qubit rotation angles to [-π, π] #13
* Add `offline_simulator_no_noise` resource (based on Qiskit-Aer simulator) to all workspaces #16
* Add simple execution tests #16
* Use native support for arbitrary-angle RXX gates #19
* Stricter validation of measurement operations #19
* Allow executing circuits with only measurement operations #19

## qiskit-aqt-provider v0.7.0

* Fix quantum/classical registers mapping #10
* Allow jobs with multiple circuits #10
* Use `poetry` for project setup #7

## qiskit-aqt-provider v0.6.1

* Fixes installation on windows #8

## qiskit-aqt-provider v0.6.0

* Initial support for the Arnica API #4
* Setup Mypy typechecker #3
