from qiskit import QuantumCircuit, execute

from qiskit_aqt_provider import AQTProvider

circuit = QuantumCircuit(2)
circuit.h(0)
circuit.cx(0, 1)
circuit.measure_all()

provider = AQTProvider("ACCESS_TOKEN")
backend = provider.get_backend("offline_simulator_no_noise")

job = execute(circuit, backend)
result = job.result()

if result.success:
    counts = result.get_counts()
    print(counts)

else:
    raise RuntimeError

circuit2 = QuantumCircuit(3)
circuit2.h(0)
circuit2.cx(0, 1)
circuit2.cx(1, 2)
circuit2.measure_all()

batch = [circuit, circuit2]

job2 = execute(batch, backend)
print(job2.progress())
result2 = job2.result()
print(result2.get_counts())
