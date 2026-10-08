"""Capacidad, exenciones, asignación GDP, retrasos y KPIs."""
import numpy as np
from config import AAR, PAAR, Hstart, Hend, margin
from emissions import airEmissions, groundEmissions



def computeHNoReg(eta):#Calculates minute per minute the arrived planes & how many could have landed with the avaiable capacity
    t = np.arange(0, 1441)  # every minute of the day
    demand = np.array([np.sum(eta <= x) for x in t])  # aircraft arrived up to minute x
    capacity = demand.astype(float)  # before Hstart capacity = demand
    d0 = demand[Hstart * 60]
    during = (t > Hstart * 60) & (t <= Hend * 60)
    after = t > Hend * 60
    capacity[during] = d0 + (t[during] - Hstart * 60) * PAAR / 60
    capacity[after] = d0 + (Hend - Hstart) * PAAR + (t[after] - Hend * 60) * AAR / 60
    HNoReg = t[(t >= Hend * 60) & (capacity >= demand)][0]  # capacity catches up with demand
    queue = np.maximum(demand - capacity, 0)  # aircraft waiting at each minute
    total_delay = queue[(t >= Hstart * 60) & (t <= HNoReg)].sum()
    return t, demand, capacity, HNoReg, total_delay


def computeSlots(HNoReg):
    slots = []
    time = Hstart * 60.0
    while time <= HNoReg + 60:  # one extra hour of slots as a safety margin
        slots.append([round(time, 2), 0, 0])
        time += 60 / PAAR if time < Hend * 60 else 60 / AAR
    return np.array(slots, dtype=object)


def determineFlightStatus(arr, Hfile, HNoReg, radius):
    NotAffected, ExemptRadius, ExemptInternational, ExemptFlying, Controlled = [], [], [], [], []
    for flight_id, flight in arr.iterrows():
        if flight['ETA_min'] < Hstart * 60 or flight['ETA_min'] > HNoReg:
            NotAffected.append(flight_id)
        elif flight['Distance'] > radius:
            ExemptRadius.append(flight_id)
        elif flight['NonECAC']:
            ExemptInternational.append(flight_id)
        elif flight['ETD_min'] < Hfile * 60 + margin:
            ExemptFlying.append(flight_id)
        else:
            Controlled.append(flight_id)
    Exempt = ExemptRadius + ExemptInternational + ExemptFlying
    return NotAffected, ExemptRadius, ExemptInternational, ExemptFlying, Exempt, Controlled


def assignSlotsGDP(slots, Controlled, Exempt, arrivals):
    #slots[time,id,company]
    slot_time = slots[:, 0].astype(float)
    used_slots = np.zeros(len(slots), dtype=bool)#Vector bool per tenir un registre dels ocupats
    CTA = arrivals['ETA_min'].copy()
    GroundDelay = []
    AirDelay = []
#Ordena per prioritat. 1.Exempts 2.Controlled ordenats per ETA.
    for id in sorted(Exempt) + sorted(Controlled):
        eta = arrivals.loc[id, 'ETA_min']
       #Cerca el primer slot not used_slots & hora>=eta.
        first_free_slot = np.where(~used_slots & (slot_time >= eta))[0]
        #Si no queda cap slot lliure posterior a l'ETA del vol, mostra un avís per pantalla i salta al següent vol
        if len(first_free_slot) == 0:
            print(f"Warning: no slot left for flight {arrivals.loc[id, 'ARCID']}")
            continue
        k = first_free_slot[0]
        used_slots[k] = True #Marquem slot[k] com a utilitzat
        slots[k, 1] = id
        slots[k, 2] = arrivals.loc[id, 'Compañía']
        CTA[id] = slot_time[k] #Assignació nou temps d'arribada
        delay = round(float(slot_time[k] - eta), 2)
        if id in Controlled:
            GroundDelay.append([id, delay])
        else:
            AirDelay.append([id, delay])
    return slots, np.array(GroundDelay, dtype=object), np.array(AirDelay, dtype=object), CTA


def delayStatistics(delay_list):
    #Agafem el segon element de flight[1] que es el min_delay. List.
    delay_minutes = np.array([flight[1] for flight in delay_list], dtype=float)
    if len(delay_minutes) == 0:
        return 0.0, 0.0, 0.0, 0.0
    # Calculate the 4 statistical metrics
    total_delay_minutes = delay_minutes.sum()
    maximum_delay_minutes = delay_minutes.max()
    mean_delay_minutes = delay_minutes.mean()
    # Relative standard deviation (%) to measure dispersion
    standard_deviation = delay_minutes.std()
    relative_std_percent = (100 * standard_deviation / mean_delay_minutes) if mean_delay_minutes > 0 else 0.0 #Evitem divisió per un zero
    return total_delay_minutes, maximum_delay_minutes, mean_delay_minutes, relative_std_percent


def unrecoverableDelay(arrivals, GroundDelay):
    unrecoverable = []
    for id, gd in GroundDelay: #id i gd per vol
        etd = arrivals.loc[id, 'ETD_min'] #extreiem id, ETD
        if etd >= Hstart * 60:  # case 1: the flight had not left, all delay recovered
            unrec = 0.0
        elif etd + gd <= Hstart * 60:  # case 2: the whole delay was already spent
            unrec = gd
        else:  # case 3: only the part before Hstart is lost
            unrec = Hstart * 60 - etd
        unrecoverable.append([id, round(float(unrec), 2)])
    return np.array(unrecoverable, dtype=object)


def gdpKPIs(arrivals, Hfile, radius, HNoReg):#Ajuntem les funcions anteriors, apliquem el gdp per un valor Hfile i radi i retorna 6 indicadors dels mapes de calor
    status = determineFlightStatus(arrivals, Hfile, HNoReg, radius)
    #STATUS: 5 -> ControlledFlight 4->Exempt in assignSlotsGDP
    slots, GroundDelay, AirDelay, CTA = assignSlotsGDP(computeSlots(HNoReg), status[5], status[4], arrivals)
    min_airdelay = sum(delay for _, delay in AirDelay)
    min_groundelay = sum(delay for _, delay in GroundDelay)
    #Cridem la funció i calculem casos 1,2,3
    min_unrecoverableDelay = sum(unrec for _, unrec in unrecoverableDelay(arrivals, GroundDelay))
    co2_air = airEmissions(arrivals, AirDelay)[1] #Segona posició tupla [1]
    co2_ground = groundEmissions(arrivals, GroundDelay)[1]
    return [min_airdelay, min_groundelay, min_unrecoverableDelay, co2_air, co2_ground, co2_air + co2_ground]
