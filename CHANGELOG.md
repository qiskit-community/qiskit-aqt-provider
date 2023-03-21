# Changelog

## Unreleased

* Fix and improve error handing from individual circuits #24
* Run the examples in the continuous integration pipeline #26
* Add `number_of_qubits` to the `quantum_circuit` job payload #29

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
