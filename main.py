flight_data_file = open("noFinsADAS1.csv", "r")
flight_data = [(datum[0], datum[1]) for datum in [
    [float(datum) for datum in line.split(",") if datum.strip()] for line in flight_data_file.readlines() if
    not line.startswith("#") and 18 > float(line.split(",")[0]) > 4
]]

didx = 0
import time 
import board
import busio
import adafruit_bmp3xx
# TODO @pablo add in altimeter and sensor reading
def get_altitude():
    global didx

    i2c = busio.I2C(board.SCL, board.SDA)
    bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)
    while True:
        print("Pressure: {:6.1f}".format(bmp.pressure))         # Don't need to print values 
        print("Temperature: {:5.2f}".format(bmp.temperature))

        bmp.sea_level_pressure = 1013.25 #This constant value needs to be updated based on launch location
        print("Altitude: {} meters".format(bmp.altitude))
        time.sleep(2)


    """
    Just ask the onboard Amishi lol !!!!!!!!!!!!lol
    """
    datum = flight_data[didx]
    didx += 1
    return datum

    return (time.time, bmp.altitude)

# TODO @nghia and mathew replace with polynomial gradient descent
def do_quadratic_least_squares_regression(data):
    """
    Perform a quadratic regression on the data and return the coefficients for standard form
    Elizabeth (Ms. Rakotyanskaya) wrote this   ✌(◕‿-)✌ DEAD INSIDE 
    https://www.easycalculation.com/statistics/learn-quadratic-regression.php
    https://www.azdhs.gov/documents/preparedness/state-laboratory/lab-licensure-certification/technical-resources/calibration-training/12-quadratic-least-squares-regression-calib.pdf
    """
    # very general
    x = [datum[0] for datum in data]
    y = [datum[1] for datum in data]
    n = len(data)
    ex = sum(x)  # se oh wait no nvm
    ey = sum(y)  # xy
    ex2 = sum([ts ** 2 for ts in x])  # TODO optimise multiplications
    ex3 = sum([ts ** 3 for ts in x])
    ex4 = sum([ts ** 4 for ts in x])
    exy = sum([x * y for x, y in data])
    ex2y = sum([(x ** 2) * y for x, y in data])
    exx = ex2 - ((ex ** 2) / n)
    exy = exy - ((ex * ey) / n)
    exx2 = ex3 - ((ex2 * ex) / n)
    ex2y = ex2y - ((ex2 * ey) / n)
    ex2x2 = ex4 - ((ex2 ** 2) / n)
    a = ((ex2y * exx) - (exy * exx2)) / ((exx * ex2x2) - (exx2 ** 2))
    b = ((exy * ex2x2) - (ex2y * exx2)) / ((exx * ex2x2) - (exx2 ** 2))
    c = ((ey / n) - (b * (ex / n)) - (a * (ex2 / n)))

    """
    Perform a quadratic regression on the data and return the coefficients for standard form
    
    https://www.easycalculation.com/statistics/learn-quadratic-regression.php
    https://www.azdhs.gov/documents/preparedness/state-laboratory/lab-licensure-certification/technical-resources/calibration-training/12-quadratic-least-squares-regression-calib.pdf
    
    a*x^1.5 + bx + c
    """
    print(a, b, c)
    return a, b, c


def log_frame(time, altitude, predicted_apogee):
    pass


def quadratic(a, b, c, x):
    """
    Evaluate a quadratic equation at the specified point
    """
    return a * x * x + b * x + c


# Flight data for regression
altitude_buffer = flight_data

# PID variables
integral_total = 0
last_time = None
last_error = None

# Safety code
MAX_RUNTIME_AT_CALIBRATE = 10  # seconds
CALIBRATE_SPEED = 0.1  # duty cycle

SAFEST_POSITION = MAX_RUNTIME_AT_CALIBRATE * CALIBRATE_SPEED

motor_position = 0
m_throttle = 0

# Main code
#while True:
    # TODO @pblo wait until launch is detected
"""
if sensor.linear_acceleration[2] > 50:
        launch_detected = True
     
         * The time to wait before simulating fin deployment
          
"""
        # val DEPLOYMENT_DELAY = 5.seconds
    time.sleep(5)           # The time to wait before simulating fin deployment

    time, altitude = get_altitude()
    altitude_buffer.append((time, altitude))

    if len(altitude_buffer) < 3:
        continue

    # TODO @pablo add code to wait until motor burnout 5 s into flight
    time.sleep(5) 

    a, b, c = do_quadratic_least_squares_regression(altitude_buffer)

    # TODO @nghia and mthew polynomial maxima x-coordinate (-b/1.5a)^2

    x_of_apex = -b / (2 * a)

    # pid goes here
    predicted_apogee = quadratic(a, b, c, x_of_apex) # TODO @nghia and mathew replace with polynomial evaluation at x_of_apex

    # maybe unit conversion from meters or whatever cheese to feet
    pid_error = predicted_apogee - 5280 # TODO @nghia and mathew check units are the same

    kP = 1
    kI = 0
    kD = 0

    # TODO @aanand test PID code

    P = pid_error * kP
    I = kI * integral_total

    derivative_term = 0
    if last_error is not None:
        dT = time - last_time
        dE = pid_error - last_error
        derivative_term = dE / dT
        integral_total += pid_error * dT
        # TODO @aanand update to match openrocket listener simulation
        motor_position += m_throttle * dT
        m_throttle = 0
        D = kD * derivative_term
        m_throttle_unsafe = - (P + I + D)
        # motor safety positional code goes here

        if (motor_position + m_throttle_unsafe * dT) < SAFEST_POSITION:
            m_throttle = m_throttle_unsafe

        # motor magic yadda yadda

    last_error = pid_error
    last_time = time

    log_frame(time, altitude, predicted_apogee)