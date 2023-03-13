# Changelog

## Unreleased

* Allow the transpiler to decompose any series of single-qubit rotations as ZRZ #13
* Wrap single-qubit rotation angles to [-π, π] #13
* Add `offline_simulator_no_noise` resource (based on Qiskit-Aer simulator) to all workspaces #16
* Add simple execution tests #16

## qiskit-aqt-provider v0.7.0

* Fix quantum/classical registers mapping #10
* Allow jobs with multiple circuits #10
* Use `poetry` for project setup #7

## qiskit-aqt-provider v0.6.1

* Fixes installation on windows #8

## qiskit-aqt-provider v0.6.0

* Initial support for the Arnica API #4
* Setup Mypy typechecker #3
