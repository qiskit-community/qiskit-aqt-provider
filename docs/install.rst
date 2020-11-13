==================================
Installing the Qiskit AQT provider
==================================

Installation
============

Installation is typically just:

.. code-block::

    pip install qiskit-aqt-provider

Installing from source is also straightforward:

.. code-block::

    python setup.py install


Requirements
============

The Qiskit AQT provider requires installing the base qiskit
package, as well as the `requests` library for making HTTP
requests.

- qiskit-terra >= 0.16.0
- requests >= 2.19


AQT backend access token
========================

Although not technically part of the installation process,
submitting circuits to the AQT systems and simulators
requires having `AQT Cloud Access <https://gateway-portal.aqt.eu/>`_
and a backend subscription.