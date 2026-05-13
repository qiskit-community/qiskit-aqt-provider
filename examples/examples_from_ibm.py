from itertools import combinations

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit import Parameter
from qiskit.circuit.library import efficient_su2, iqp, qaoa_ansatz, real_amplitudes
from qiskit.quantum_info import SparsePauliOp, random_hermitian

from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.primitives.estimator import AQTEstimator
from qiskit_aqt_provider.primitives.sampler import AQTSampler

backend = AQTProvider().get_backend("offline_simulator_no_noise")
num_qubits = 10


#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples#run-a-single-experiment
#################

mat = np.real(random_hermitian(num_qubits, seed=1234))
circuit = iqp(mat)
observable = SparsePauliOp("Z" * num_qubits)

estimator = AQTEstimator(backend=backend)
job = estimator.run([(circuit, observable)])
result = job.result()

print(f" > Expectation value: {result[0].data.evs}")
print(f" > Metadata: {result[0].metadata}")


#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples#run-multiple-experiments-in-a-single-job
#################

rng = np.random.default_rng()
mats = [np.real(random_hermitian(num_qubits, seed=rng)) for _ in range(3)]

pubs = []
circuits = [iqp(mat) for mat in mats]
observables = [
    SparsePauliOp("X" * num_qubits),
    SparsePauliOp("Y" * num_qubits),
    SparsePauliOp("Z" * num_qubits),
]

for qc, obs in zip(circuits, observables):
    pubs.append((qc, obs))

estimator = AQTEstimator(backend=backend)
job = estimator.run(pubs)
job_result = job.result()

for idx in range(len(pubs)):
    pub_result = job_result[idx]
    print(f">>> Expectation values for PUB {idx}: {pub_result.data.evs}")
    print(f">>> Standard errors for PUB {idx}: {pub_result.data.stds}")


#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples#run-parameterized-circuits
#################

theta = Parameter("θ")

chsh_circuit = QuantumCircuit(2)
chsh_circuit.h(0)
chsh_circuit.cx(0, 1)
chsh_circuit.ry(theta, 0)

number_of_phases = 21
phases = np.linspace(0, 2 * np.pi, number_of_phases)
individual_phases = [[ph] for ph in phases]

ZZ = SparsePauliOp.from_list([("ZZ", 1)])
ZX = SparsePauliOp.from_list([("ZX", 1)])
XZ = SparsePauliOp.from_list([("XZ", 1)])
XX = SparsePauliOp.from_list([("XX", 1)])
ops = [ZZ, ZX, XZ, XX]

# Step 3: Execute using Qiskit primitives.

# Reshape observable array for broadcasting
reshaped_ops = np.fromiter(ops, dtype=object)
reshaped_ops = reshaped_ops.reshape((4, 1))

estimator = AQTEstimator(backend=backend)
job = estimator.run([(chsh_circuit, reshaped_ops, individual_phases)])
# Get results for the first (and only) PUB
pub_result = job.result()[0]
print(f">>> Expectation values: {pub_result.data.evs}")
print(f">>> Standard errors: {pub_result.data.stds}")
print(f">>> Metadata: {pub_result.metadata}")


#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples#run-a-single-experiment-1
#################

mat = np.real(random_hermitian(num_qubits, seed=1234))
circuit = iqp(mat)
circuit.measure_all()

sampler = AQTSampler(backend=backend)
job = sampler.run([circuit])
result = job.result()

# Get results for the first (and only) PUB
pub_result = result[0]

print(f" > First ten results: {pub_result.data.meas.get_bitstrings()[:10]}")

#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples#run-multiple-experiments-in-a-single-job-1
#################

rng = np.random.default_rng()
mats = [np.real(random_hermitian(num_qubits, seed=rng)) for _ in range(3)]
circuits = [iqp(mat) for mat in mats]
for circuit in circuits:
    circuit.measure_all()


sampler = AQTSampler(backend=backend)
job = sampler.run(circuits)
result = job.result()

for idx, pub_result in enumerate(result):
    print(f" > First ten results for pub {idx}: {pub_result.data.meas.get_bitstrings()[:10]}")

#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitives-examples#run-parameterized-circuits-1
#################

# Step 1: Map classical inputs to a quantum problem
circuit = real_amplitudes(num_qubits=num_qubits, reps=2)
circuit.measure_all()

# Define three sets of parameters for the circuit
rng = np.random.default_rng(1234)
parameter_values = [rng.uniform(-np.pi, np.pi, size=circuit.num_parameters) for _ in range(3)]

# Step 3: Execute using Qiskit primitives.
sampler = AQTSampler(backend=backend)
job = sampler.run([(circuit, parameter_values)])
result = job.result()
# Get results for the first (and only) PUB
pub_result = result[0]
# Get counts from the classical register "meas".
print(
    f" >> First ten results for the meas output register: {pub_result.data.meas.get_bitstrings()[:10]}"
)


#################
# https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-primitives#get-started-with-estimator
#################

# All-to-all connectivity (fully connected graph)
entanglement = list(combinations(range(num_qubits), 2))

observable = SparsePauliOp.from_sparse_list(
    [("ZZ", [i, j], 0.5) for i, j in entanglement],
    num_qubits=num_qubits,
)

circuit = qaoa_ansatz(observable, reps=2)
# the circuit is parametrized, so we will define the parameter values for execution
param_values = [0.1, 0.2, 0.3, 0.4]

print(f">>> Observable: {observable.paulis}")

# Instantiate an estimator on the execution backend
estimator = AQTEstimator(backend=backend, optimization_level=3)

job = estimator.run([(circuit, observable, param_values)], precision=0.022365)
print(f">>> Job ID: {job.job_id()}")
print(f">>> Job Status: {job.status()}")

result = job.result()
print(f">>> {result}")
print(f"  > Expectation value: {result[0].data.evs}")
print(f"  > Metadata: {result[0].metadata}")

#################
# https://quantum.cloud.ibm.com/docs/en/guides/get-started-with-primitives#get-started-with-sampler
#################


circuit = efficient_su2(10, entanglement="linear")
circuit.measure_all()
# The circuit is parametrized, so we will define the parameter values for execution
param_values = np.random.rand(circuit.num_parameters)  # noqa

sampler = AQTSampler(backend=backend)

job = sampler.run([(circuit, param_values)])
print(f">>> Job ID: {job.job_id()}")
print(f">>> Job Status: {job.status()}")

print(circuit)

result = job.result()

# Get results for the first (and only) PUB
pub_result = result[0]
print(
    f"First ten results for the 'meas' output register: {pub_result.data.meas.get_bitstrings()[:10]}"
)


#################
# https://quantum.cloud.ibm.com/docs/en/api/qiskit-ibm-runtime/estimator-v2
#################

psi = real_amplitudes(num_qubits=2, reps=2)
hamiltonian = SparsePauliOp.from_list([("II", 1), ("IZ", 2), ("XI", 3)])
theta = [0, 1, 1, 2, 3, 5]

observables = hamiltonian.apply_layout(psi.layout)

estimator = AQTEstimator(backend=backend)

# calculate [ <psi(theta)|hamiltonian|psi(theta)> ]
job = estimator.run([(psi, observables, [theta])])
pub_result = job.result()[0]
print(f"Expectation values: {pub_result.data.evs}")


#################
# from https://quantum.cloud.ibm.com/docs/en/guides/primitive-input-output#sampler-output
#################

circuit = QuantumCircuit(10)
circuit.h(0)
circuit.cx(range(9), range(1, 10))

# append measurements with the `measure_all` method
circuit.measure_all()

sampler = AQTSampler(backend=backend)

# run the Sampler job and retrieve the results

job = sampler.run([circuit])
result = job.result()

# the data bin contains one BitArray
data = result[0].data
print(f"Databin: {data}\n")

# to access the BitArray, use the key "meas", which is the default name of
# the classical register when this is added by the `measure_all` method
array = data.meas
print(f"BitArray: {array}\n")
print(f"The shape of register `meas` is {data.meas.array.shape}.\n")
print(f"The bytes in register `meas`, shot by shot:\n{data.meas.array}\n")


# generate a ten-qubit GHZ circuit with two classical registers
circuit = QuantumCircuit(
    qreg := QuantumRegister(10),
    alpha := ClassicalRegister(1, "alpha"),
    beta := ClassicalRegister(9, "beta"),
)
circuit.h(0)
circuit.cx(range(9), range(1, 10))

# append measurements with the `measure_all` method
circuit.measure([0], alpha)
circuit.measure(range(1, 10), beta)

# run the Sampler job and retrieve the results
job = sampler.run([circuit])
result = job.result()

# the data bin contains two BitArrays, one per register, and can be accessed
# as attributes using the registers' names
data = result[0].data
print(f"BitArray for register 'alpha': {data.alpha}")
print(f"BitArray for register 'beta': {data.beta}")


# Print out the results metadata
print("The metadata of the PrimitiveResult is:")
for key, val in result.metadata.items():
    print(f"'{key}' : {val},")

print("\nThe metadata of the PubResult result is:")
for key, val in result[0].metadata.items():
    print(f"'{key}' : {val},")


#################
# https://quantum.cloud.ibm.com/docs/en/guides/primitive-input-output
#################

# Define a circuit with two parameters.
circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.ry(Parameter("a"), 0)
circuit.rz(Parameter("b"), 0)
circuit.cx(0, 1)
circuit.h(0)

# Now define a sweep over parameter values, the last axis of dimension 2 is
# for the two parameters "a" and "b"
params = np.vstack(
    [
        np.linspace(-np.pi, np.pi, 10),
        np.linspace(-4 * np.pi, 4 * np.pi, 10),
    ]
).T

# Define three observables. The inner length-1 lists cause this array of
# observables to have shape (3, 1), rather than shape (3,) if they were
# omitted.
observables = [
    [SparsePauliOp(["XX", "IT"], [0.5, 0.5])],
    [SparsePauliOp("XX")],
    [SparsePauliOp("IT")],
]

# Estimate the expectation value for all 30 combinations of observables
# and parameter values, where the pub result will have shape (3, 10).
#
# This shape is due to our array of parameter bindings having shape
# (10, 2), combined with our array of observables having shape (3, 1).
estimator = AQTEstimator(backend=backend)
estimator_pub = (circuit, observables, params)

# Run the transpiled circuit
# using the set of parameters and observables.

job = estimator.run([estimator_pub])
result = job.result()
print(f"The result of the submitted job had {len(result)} PUB and has a value:\n {result}\n")
print(f"The associated PubResult of this job has the following data bins:\n {result[0].data}\n")
print(f"And this DataBin has attributes: {result[0].data.keys()}")
print(
    print(
        "Recall that this shape is due to our array of parameter binding sets having shape (10, 2) -- where 2 is the\n\
         number of parameters in the circuit -- combined with our array of observables having shape (3, 1). \n"
    )
)
print(f"The expectation values measured from this PUB are: \n{result[0].data.evs}")
