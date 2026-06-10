.. _offline:

==================
Offline Simulators
==================

This guide covers usage of the Qiskit AQT provider package with the offline AQT simulators.

.. _offline-usage:
Usage
=====

The offline simulator provider provides access to ideal and noisy simulators that are running locally. 

.. code-block:: python

    from qiskit_aqt_provider import AQTProvider

    provider = AQTProvider()
    ideal_simulator_backend = provider.offline.ideal()
    noisy_simulator_backend = provider.offline.noisy()

These simulators are ideal for testing and debugging your quantum circuits without needing access to a real quantum computer. The ideal simulator will give you the exact results of your quantum circuit, while the noisy simulator will include realistic noise models to help you understand how your circuit might perform on actual hardware.

.. note::

    When you are ready to run your circuits on real quantum hardware, be sure to read the appropriate guide (:ref:`cloud<cloud-usage>` or :ref:`direct<direct-usage>`), as backend acquisition is slightly different.



Quantum register size
=====================

By default, offline simulator are configured with 20 qubits. Changing the size of the simulated quantum register is not currently supported.
