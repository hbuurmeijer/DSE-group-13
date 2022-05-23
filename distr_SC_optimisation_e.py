import numpy as np
import pandas as pd
from scipy.optimize import fsolve
from matplotlib import pyplot as plt

# Define constants
R_e = 6378.137e3  # [m]
g_0 = 9.80665  # [m/s2]
mu = 3.986004418e14  # [m3/s2]
h_collision = 789e3  # [m]
debris_n = 10
a_collision = R_e + h_collision

# Import the reference data
debris_info = pd.read_csv("iridium_cosmos_result.csv")
debris_info = debris_info.loc[debris_info["Name"] == 'Kosmos 2251-Collision-Fragment']  # Only Kosmos fragments
debris_info = debris_info[["Semi-Major-Axis [m]", "Eccentricity", "Inclination [rad]",
                           "Longitude of the ascending node [rad]", "Argument of periapsis [rad]", "Mean Anomaly [rad]"]]
debris_info["Removed"] = np.zeros(len(debris_info["Semi-Major-Axis [m]"]))
debris_info = debris_info.loc[debris_info["Semi-Major-Axis [m]"] > a_collision]  # - 60e3
debris_info = debris_info.head(debris_n)
index_list = debris_info.index.tolist()
debris_info = debris_info.to_numpy()


def getPosition(a, e, t, M_0):
    '''
    Find the position of the spacecraft in the Keplerian system.
    @param: a, e, t
    @return: true_anomaly, the true anomaly of the spacecraft at time t
    '''
    n = np.sqrt(mu / a ** 3)  # Mean motion
    M = n*t - M_0
    # Solve the equation numerically
    func = lambda E: E - e * np.sin(E) - M
    init_guess = 3
    E = fsolve(func, init_guess)  # , xtol=0.001
    E = E[0]
    # Final equation
    true_anomaly = 2 * np.arctan(np.sqrt((1 + e) / (1 - e)) * np.tan(E / 2))
    return true_anomaly


def KeplerToCartesian(a, e, w, true_anomaly, i, RAAN, position):
    '''
    Convert a position in the Keplerian system to a cartesian system
    @param: true_anomaly, the true anomaly of the spacecraft at time t
    '''

    p = a * (1-e**2)
    r = p/(1 + e * np.cos(true_anomaly))  # radius

    # Compute the Cartesian position vector
    position[:, 0] = r * (np.cos(RAAN) * np.cos(w + true_anomaly) - np.sin(RAAN) * np.sin(
        w + true_anomaly) * np.cos(i))
    position[:, 1] = r * (np.sin(RAAN) * np.cos(w + true_anomaly) + np.cos(RAAN) * np.sin(
        w + true_anomaly) * np.cos(i))
    position[:, 2] = r * (np.sin(i) * np.sin(w + true_anomaly))
    return position


t0 = 30*100*60
t = t0
dt = 50
debris_counter = 0
distance_sc = 40e3
# Spacecraft variables
a_sc = R_e + h_collision + distance_sc
w_sc = 0
e_sc = 0
i_sc = np.average(debris_info[:, 2])
RAAN_sc = np.average(debris_info[:, 3])
M_0_sc = 0

ts = []
percentages = np.array([])
position_sc = np.zeros([1, 3])
position_debris = np.zeros((len(debris_info[:, 0]), 3))
debris_true_anomalies = np.zeros(len(debris_info[:, 0]))

while debris_counter/debris_n < 0.822231:
    ts.append(t)

    # Compute spacecraft position
    true_anomaly_sc = getPosition(a_sc, e_sc, t, M_0_sc)
    pos_sc = KeplerToCartesian(a_sc, e_sc, w_sc, true_anomaly_sc, i_sc, RAAN_sc, position_sc)

    active_debris_idx = np.isclose(debris_info[:, 6], 0)  # Extract only "active" debris objects
    reduced_debris_info = debris_info[active_debris_idx]

    for i in range(reduced_debris_info.shape[0]):
        debris_true_anomalies[i] = getPosition(reduced_debris_info[i, 0], reduced_debris_info[i, 1], t, reduced_debris_info[i, 5])
    pos_debris = KeplerToCartesian(reduced_debris_info[:, 0], reduced_debris_info[:, 1], reduced_debris_info[:, 4], debris_true_anomalies[active_debris_idx],
                                       reduced_debris_info[:, 2], reduced_debris_info[:, 3], position_debris[active_debris_idx])
    rel_pos = pos_debris - pos_sc
    abs_distance = np.linalg.norm(rel_pos, axis=1)
    reduced_debris_info[abs_distance < 100e3, 6] = 1
    debris_info[active_debris_idx] = reduced_debris_info

    t += dt

    debris_counter = debris_info.shape[0] - reduced_debris_info.shape[0]
    percentages = np.append(percentages, debris_counter/debris_n)

    print("--------------------------------------------")
    print(round((t - t0)/3600, 2))
    if (round(t))%2 == 0:
        print(debris_counter)
        print(str(round(debris_counter/debris_n*100, 2)) + '%')


plt.figure()
plt.plot((np.array(ts) - t0)/3600, percentages*0.6)
plt.xlabel('Time [hr]')
plt.ylabel('Percentage of debris removed [%]')
plt.grid()
plt.show()