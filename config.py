"""Central configuration for the LIRF project."""
from pathlib import Path

# Put the CSV next to main.py, or edit this path.
filename = r'C:\Users\Dani\Downloads\LIRF_10AUG2025_2111_molina.csv'
airport = 'LIRF'
AAR = 49
PAAR = 20
Hstart = 8
Hend = 13
Hfile = Hstart - 2
radius = 1000
margin = 30
apu_fuel = {'A': 500.0, 'B': 300.0, 'C': 220.0, 'D': 130.0, 'E': 60.0, 'F': 0.0}
