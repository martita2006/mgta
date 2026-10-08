# LIRF en 5 módulos Python

1. Coloca `LIRF_10AUG2025_2111_molina.csv` junto a `main.py`.
2. Abre esta carpeta en PyCharm e instala: `python -m pip install -r requirements.txt`.
3. Ejecuta `main.py`.

- `config.py`: parámetros del escenario.
- `data.py`: importación, limpieza y conversión ETA/ETD (fracciones de día * 24 * 60).
- `gdp.py`: capacidad, slots, exenciones, retrasos y KPIs.
- `emissions.py`: fórmulas de emisiones ASK y cálculo de emisiones aire/tierra.
- `main.py`: checkpoints, resultados, optimización y gráficos.

Este es un reagrupamiento de la versión modular anterior, manteniendo su lógica. La conversión ETA/ETD requiere un CSV con tiempos en fracciones de día.
