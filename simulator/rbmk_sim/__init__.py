"""
rbmk_sim — RBMK-class point-kinetics simulator
================================================
Composite model assembled from cited literature (B1–B4, B8/B9, EPJ-N 2023).
All parameters are LOCKED per DESIGN_DECISIONS.md (D1–D10).

Modules
-------
params      : frozen physical constants and coefficients
kinetics    : six-group point-kinetics + Xe/I ODEs
feedback    : reactivity feedback terms (void, Doppler, xenon)
scenarios   : normal-operation and anomaly scenario builders
simulator   : top-level Simulator class (run, validate, generate)
"""
