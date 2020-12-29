import matplotlib.pyplot as plt
import pandas as pd

imu_time = 5

flight_data_file = open("noFinsADAS1.csv", "r")
flight_data = [
    [float(datum) for datum in line.split(",") if datum.strip()] for line in flight_data_file.readlines() if
    not line.startswith("#") and float(line.split(",")[0]) < imu_time
]

# print(flight_data)

preflight_data = []
for i in range(2, 6):
    preflight_file = open(f"noFinsADAS{i}.csv", "r")
    preflight_data.append([
        [float(datum) for datum in line.split(",") if datum.strip()] for line in preflight_file.readlines() if
        not line.startswith("#") and float(line.split(",")[0]) < imu_time
    ])

# print(preflight_data)

for preflight in preflight_data:
    chi_square = 0

    for i in range(0, len(preflight)):
        index = min(len(flight_data) - 1, i)
        flight_frame = flight_data[index]
        otime, oaltitude, oaccel = flight_frame
        preflight_frame = preflight[i]
        if preflight_frame[1] == 0:
            continue
        etime, ealtitude, evelocity, eaccel = preflight[i]

        chi_square += ((oaltitude - ealtitude) ** 2) / ealtitude

    print(chi_square)

current_closest_time = []

if __name__ == '__main__':
    pass
