"""Run checkpoints 1-4 for LIRF. Keep the CSV beside this file."""
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from config import filename, airport, AAR, PAAR, Hstart, Hend, Hfile, radius
from data import readArrivals
from gdp import (computeHNoReg, computeSlots, determineFlightStatus, assignSlotsGDP,
                 delayStatistics, unrecoverableDelay, gdpKPIs)
from emissions import airEmissions, groundEmissions

def plotHistogram(hours, title):
    plt.figure()
    plt.hist(hours, bins=np.arange(0, 25, 1), edgecolor='black')
    plt.plot([0, Hstart], [AAR, AAR], 'g-', linewidth=3, label=f'AAR = {AAR}')
    plt.plot([Hend, 24], [AAR, AAR], 'g-', linewidth=3)
    plt.plot([Hstart, Hend], [PAAR, PAAR], 'r-', linewidth=3, label=f'PAAR = {PAAR}')
    plt.xlabel('Time [h]')
    plt.ylabel('Number of arrivals')
    plt.title(title)
    plt.xlim(0, 24)
    plt.grid(True)
    plt.legend(loc='upper left')


np.set_printoptions(threshold=np.inf, suppress=True)


def main():
    # Checkpoints 1 and 2: demand, aggregate curves and HNoReg
    radius = 1000
    arrivals = readArrivals(filename)
    plotHistogram(arrivals['ETA_min'] / 60, f'Arrival demand at {airport} (initial)')

    t, demand, capacity, HNoReg, total_delay = computeHNoReg(arrivals['ETA_min'].values)
    affected = np.sum((arrivals['ETA_min'] >= Hstart * 60) & (arrivals['ETA_min'] <= HNoReg))
    print(f'HNoReg: {HNoReg // 60:02d}:{HNoReg % 60:02d} h')
    print(f'Theoretical total delay: {total_delay:.2f} min')
    print(f'Affected flights: {affected}')
    print(f'Theoretical average delay: {total_delay / affected:.2f} min/flight')

    plt.figure()
    plt.plot(t / 60, demand, 'g-', linewidth=2, label='Aggregate demand')
    plt.plot(t / 60, np.minimum(capacity, demand), 'r:', linewidth=2, label='Aggregate capacity')
    for x, c, name in [(Hfile, 'gray', 'Hfile'), (Hstart, 'orange', 'Hstart'),
                       (Hend, 'purple', 'Hend'), (HNoReg / 60, 'blue', 'HNoReg')]:
        plt.axvline(x=x, color=c, linestyle='--', label=name)
    plt.xlabel('Time [h]')
    plt.ylabel('Cumulative number of aircraft')
    plt.title('Aggregate demand and capacity')
    plt.xlim(0, 24)
    plt.grid(True)
    plt.legend(loc='upper left')

    # Checkpoint 3: GDP with the initial Hfile and radius
    NotAffected, ExemptRadius, ExemptInternational, ExemptFlying, Exempt, Controlled = \
        determineFlightStatus(arrivals, Hfile, HNoReg, radius)
    slots, GroundDelay, AirDelay, CTA = assignSlotsGDP(computeSlots(HNoReg), Controlled, Exempt, arrivals)
    arrivals['CTA_min'] = CTA

    print(f'\nNot affected flights: {len(NotAffected)}')
    print(f'Controlled flights: {len(Controlled)}')
    print(f'Exempt flights: {len(Exempt)} (radius {len(ExemptRadius)}, non-ECAC '
          f'{len(ExemptInternational)}, airborne {len(ExemptFlying)})')
    for name, delays in [('Ground', GroundDelay), ('Air', AirDelay)]:
        total, maximum, mean, rel_std = delayStatistics(delays)
        print(f'{name} delay: total {total:.2f} min, max {maximum:.2f} min, '
              f'mean {mean:.2f} min, relative std {rel_std:.1f} %')
    print(f'Total delay (ground + air): {delayStatistics(GroundDelay)[0] + delayStatistics(AirDelay)[0]:.2f} min')
    print('\nGroundDelay [ARCID, min] =')
    print(np.array([[arrivals.loc[id, 'ARCID'], delay] for id, delay in GroundDelay], dtype=object))
    print('\nslots [time, ARCID, airline] =')
    print(np.array([[s[0], arrivals.loc[s[1], 'ARCID'] if s[1] != 0 else 0, s[2]] for s in slots], dtype=object))

    plotHistogram(arrivals['CTA_min'] / 60, 'Arrivals after the GDP (regulated traffic)')

    unrec = unrecoverableDelay(arrivals, GroundDelay)
    total_unrec = sum(u for _, u in unrec)
    print(f'\nUnrecoverable ground delay: {total_unrec:.2f} min')
    print(f'Recoverable ground delay: {delayStatistics(GroundDelay)[0] - total_unrec:.2f} min')

    fuel_air, co2_air, nox_air, sox_air, h2o_air, co_air = airEmissions(
        arrivals, AirDelay
    )
    fuel_ground, co2_ground, nox_ground, sox_ground, h2o_ground, co_ground = groundEmissions(arrivals, GroundDelay)
    # Càlcul del total d'emissions que NO són CO2 durant el retard a l'aire (en kg)
    non_co2_air = nox_air + sox_air + h2o_air + co_air
    non_co2_ground = nox_ground + sox_ground + h2o_ground + co_ground
    print(f'\nAIR DELAY EMISSIONS:')
    print(f'Fuel: {fuel_air:.2f} kg')
    print(f'CO2: {co2_air:.2f} kg')
    print(f'NOx: {nox_air:.2f} kg')
    print(f'SOx: {sox_air:.2f} kg')
    print(f'H2O (Water Vapour): {h2o_air:.2f} kg')
    print(f'CO: {co_air:.2f} kg')
    print(f'GROUND DELAY EMISSIONS:')
    print(f'Fuel: {fuel_ground:.2f} kg')
    print(f'CO2: {co2_ground:.2f} kg')
    print(f'NOx: {nox_ground:.2f} kg')
    print(f'SOx: {sox_ground:.2f} kg')
    print(f'H2O (Water Vapour): {h2o_ground:.2f} kg')
    print(f'CO: {co_ground:.2f} kg')
    print(f'TOTALS:')
    print(f'Total CO2 due to delay (Air + Ground): {co2_air + co2_ground:.2f} kg')
    print(f'Total Non-CO2 due to air delay: {non_co2_air:.2f} kg')
    print(f'Total Non-CO2 due to ground delay: {non_co2_ground:.2f} kg')
    print(f'Total Non-CO2 overall: {non_co2_air + non_co2_ground:.2f} kg')

    # Checkpoint 4: effect of Hfile and radius, heatmaps and optimal values
    hfile_range = np.arange(4, 8.5, 0.5) #Range 4:00 a les 8:00
    radius_range = np.arange(400, 2200, 200)#Radius 400 a 2000
    names = ['Air delay (min)', 'Ground delay (min)', 'Unrecoverable delay (min)',
             'CO2 air delay (kg)', 'CO2 ground delay (kg)', 'CO2 total (kg)']
    weights = [1, 0, 1, 0, 0, 1]  # KPIs used to choose the optimum (same order as names)
    maps = np.zeros((len(names), len(hfile_range), len(radius_range)))#Matriu 6x9x9
    for i, hfile in enumerate(hfile_range):#Recorrem totes les hores Hfile
        for j, radius in enumerate(radius_range): #recorre radis index j i el valor r
            maps[:, i, j] = gdpKPIs(arrivals, hfile, radius, HNoReg)
            # Funció gdpKPI i guardem els 6 resultats directament a la columna corresponent de la matriu maps

    #Matriu 9x9 per acumular puntació de hfile i radius.
    #Quan més baix score millor el cas.
    score = np.zeros((len(hfile_range), len(radius_range)))
    #Iniciem bucle per procesar cada KPI
    for k in range(len(names)): #va de 0-5 KPIs
        kpi_map = maps[k] #Taula de la KPI indicada amb el valor k.
        weight = weights[k]
        name = names[k]
        if weight == 0:
            continue # Si el pes és 0, aquest KPI no influeix en l'optimitat (ens estalviem operacions)
        min_val = kpi_map.min() #Valor min i max en el rang analitzat
        max_val = kpi_map.max()
        avg = max_val - min_val
        # Normalització Min-Max (escala de 0 a 1)
        if avg > 0:
            kpi_normalized = (kpi_map - min_val) / avg
            score += weight * kpi_normalized

    # Trobem l'índex de la posició amb el score més baix (combinació ideal)
    #Busca la posició del valor mínim dins de la matriu bidimensional
    min_val = float('inf')
    i_opt, j_opt = 0, 0
    for i in range(score.shape[0]): #Recorrem files matriu
        for j in range(score.shape[1]): #Recorrem columnes matriu
            if score[i, j] < min_val:
                min_val = score[i, j]
                i_opt, j_opt = i, j
    optimal_hfile = hfile_range[i_opt]
    optimal_radius = radius_range[j_opt]

    # Imprimim els resultats òptims per consola
    print(f'Optimal values: Hfile = {optimal_hfile:.1f} h, radius = {optimal_radius} km')
    # Imprimim els valors dels KPIs a la posició òptima
    for k in range(len(names)):
        print(f'  {names[k]}: {maps[k, i_opt, j_opt]:.2f}')

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    # Convertim els rangs en etiquetes de text netes per als eixos
    x_labels = radius_range
    y_labels = [f'{h:.1f}' for h in hfile_range]

    #Flat per agafar els grafics 0,1,2,3,4,5.
    flat_axes = axes.flat
    for k in range(len(names)):
        kpi_map = maps[k]
        name = names[k]
        ax = flat_axes[k]  # Seleccionem el subgràfic k-èssim

        # Dibuixem el heatmap
        sns.heatmap(
            kpi_map,
            ax=ax,
            cmap='Blues',
            annot=True,
            fmt='.0f',
            annot_kws={'size': 7},
            xticklabels=x_labels,
            yticklabels=y_labels
        )

        #Dibuixem un quadrat a la solució òptima
        optimal_box = plt.Rectangle((j_opt, i_opt), 1, 1, fill=False, edgecolor='red', linewidth=3)
        ax.add_patch(optimal_box)

        # Detalls estètics
        ax.set_title(name)
        ax.set_xlabel('Radius (km)')
        ax.set_ylabel('Hfile (h)')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
