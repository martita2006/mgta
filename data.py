import pandas as pd
from config import airport

def readArrivals(filename):
    df = pd.read_csv(filename, sep=';')
    arr = df[df['ADES'] == airport].copy()
    arr['ETA_min'] = pd.to_numeric(arr['ETA'], errors='coerce') * 24 * 60 #escribid esta
    arr['ETD_min'] = pd.to_numeric(arr['ETD'], errors='coerce') * 24 * 60 #escribid esta
    arr.loc[arr['ETD_min'] > arr['ETA_min'], 'ETD_min'] -= (
        1440  # flight left the day before
    )
    arr['NonECAC'] = (
        arr['ECAC SI/No'].astype(str).str.strip() == 'Fuera de ECAC'
    )

    # --- CANVI AQUÍ: Llegim directament els seients del CSV ---
    arr['Seats'] = pd.to_numeric(arr['Available seats'], errors='coerce')

    if 'Compañía' not in arr.columns:
        arr['Compañía'] = arr['ARCID'].str[
            :3
        ]  # airline taken from the flight number

    # Sort by ETA and use the position in that list as flight ID (1, 2, 3, ...)
    arr = arr.sort_values('ETA_min').reset_index(drop=True)
    arr.index = arr.index + 1
    return arr
