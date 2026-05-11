# Transpilation for AQT backends

The transpilation in the qiskit-aqt-provider is used to convert arbitrary Qiskit circuits into circuits that are compatible with AQT's backends.
The current version assumes all AQT backends have the same configuration and native gate set (R, RZ, RXX).

A circuit can be transpiled in two ways:
- use `pm = generate_preset_pass_manager(backend)` to create a pass manager and then transpile by `pm.run(circuit)` -> This is the preferred option in Qiskit 2.
- run `qiskit.compiler.transpile(backend, circuit)`

## Overview 

Qiskit allows transpilation configuration for backends by specifying the transpilation target of backends inheriting from BackendV2. The target defines:
- The native gate set
- The number of qubits
- The topology

In our case this is done in the `CloudResource` class and defines the native gates as `R`, `RZ`, `RXX` and `Measure`. The number of qubits is dynamic and the topology is fully connected.

This is already sufficient to transpile for the AQT backends with one exception. The angles of R and RXX gates need to bound to a specific range. Therefore we need to add custom transpilation passes to wrap the angles accordingly.

### Transpilation passes to wrap angles

Qiskit allows to connect [custom transpiler passes](https://quantum.cloud.ibm.com/docs/en/api/qiskit/providers#custom-transpiler-passes) to backends via [transpiler plugins](https://quantum.cloud.ibm.com/docs/en/api/qiskit/transpiler_plugins#writing-plugins). This is possible **only for the scheduling and translation stage**. We are taking advantage of this to connect the appropriate transpilation passe to AQT backends. The transpiler plugins are registered in `pyproject.toml` so Qiskit can discover them automatically and connected to the backend with:
```python
class CloudResource(BackendV2):
    def get_scheduling_stage_plugin(self) -> str:
        return "aqt"
    
    def get_translation_stage_plugin(self) -> str:
        return "aqt"
```
The transpiler plugins are defined in `transpiler_plugin.py` with `AQTTranslationPlugin` and `AQTSchedulingPlugin`. When transpiling a circuit, Qiskit includes these extra passes when it builds the transpilation pipeline. 
- The translation stage needs to do a decomposition after wrapping RXX gate angles for optimization level 0. For level 0 no further decomposition is done due to the lack of optimization.
- For optimization level > 0, the scheduling stage is the last step in the transpilation, therefore doing the angle wrapping there, ensures that the output circuit only contains valid angles.


#### Unbound parameters not supported
It is possible to define parametrized gates, which means instead of specifying a concrete angle for the gate, a parameter is used. Normal Qiskit transpilation also works for circuits with such parameterized gates. 

Our backends requirement to wrap angles during transpilation is contradicting this, as the parameters for the angles may be outside the valid ranges after binding. To make sure that a circuit is valid for AQT backends, the circuit needs to be transpiled after paramter binding, so that wrapping is done.

## Primitives
While primitives in Qiskit version 1 allow to configure actions after gate parameters are bound (with the `bound_pass_manager` parameter), Qiskit version 2 has removed this feature. In Qiskit 2, the recommended way is to pass transpiled circuits to the primitives, which then will take care of parameter binding and sending to the backend without any further transpilation.

The `AQTEstimator` and the `AQTSampler` change this behavior and do transpilation after parameter binding so that it is ensured that only valid circuits are sent to the AQT backends for processing. This automatic transpilation can be skipped with the `skip_transpilation` option when the resulting circuits only contain valid gates (from the backends native gate set and with angles in the acceptable range).

The current solution does override private functions of the generic primitives `BackendEstimatorV2` and `BackendSamplerV2` provided by Qiskit. This comes with the risk that future Qiskit versions will break the AQT primitives. This is an accepted risk until a better solution can be found. As a mitigation of that risk, the Qiskit version is pinned to a limited and tested subset. Currently Qiskit 2.3.0 to 2.4.1 are supported (see `pyproject.toml`).

### AQTEstimator
The `AQTEstimator` inherits from the `BackendEstimatorV2` and overrides the functions `_run_pubs` and `_preprocess_pub`:
- `_preprocess_pub` transpiles circuits after parameter binding before calling the same function of the parent class
- `_run_pubs` checks if the maximum amount of shots the backend is capable of, is not exceeded. Then it calls the same function of the parent class.

### AQTSampler
The `AQTSampler` inherits from the `BackendSamplerV2` and overrides the function `_run_pubs`. It copies the behavior of the parents function and adds:
- A check if the maximum amount of shots the backend is capable of, is not exceeded.
- Transpilation of circuits after parameters were bound.
- Convertion of results from binary strings to expected hex strings for postprocessing with :meth:`_postprocess_pub`.
