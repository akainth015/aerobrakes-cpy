"""
ADAS controller for 2021 SLI launches
1.  Wait for launch interrupt to trigger from IMU.
2.  Do nothing for 5 seconds. No data gathering, no fin actuation, just radio
    silence.
3.  Process frames individually, and continuously run a regression on the flight
    data from the last 2 seconds. The form of the regression is ax**1.5 + bx + c.
    The maxima of the parabola is regarded as the apogee of the flight, and the
    distance between the predicted apogee and the desired apogee of 1 mile
    (1609 meters) is passed as error to a generic PID algorithm. The output
    is clamped to within -1 and 1, then run through a safety that will
    ensure  the fins can be stopped by the next loop iteration. The
    resulting value will be passed to the motor as a duty cycle, resulting
    in safe deployment of the fins.
4.  Once we have reached apogee, retract the fins as quickly as possible still
    passing through safety code)
"""

import adafruit_bno055
import adafruit_bmp3xx
from busio import I2C
from board import SDA, SCL, D13, D4
import pwmio
from adafruit_motor import servo, motor

import time


# The following PID algorithm is copy pasted from
# https://github.com/m-lundberg/simple-pid/


def _clamp(value, limits):
    lower, upper = limits
    if value is None:
        return None
    elif upper is not None and value > upper:
        return upper
    elif lower is not None and value < lower:
        return lower
    return value


class PID:
    """A simple PID controller."""

    def __init__(
            self,
            Kp=1.0,
            Ki=0.0,
            Kd=0.0,
            setpoint=0,
            sample_time=0.01,
            output_limits=(None, None),
            auto_mode=True,
            proportional_on_measurement=False,
            error_map=None
    ):
        """
        Initialize a new PID controller.

        :param Kp: The value for the proportional gain Kp
        :param Ki: The value for the integral gain Ki
        :param Kd: The value for the derivative gain Kd
        :param setpoint: The initial setpoint that the PID will try to achieve
        :param sample_time: The time in seconds which the controller should wait before generating
            a new output value. The PID works best when it is constantly called (eg. during a
            loop), but with a sample time set so that the time difference between each update is
            (close to) constant. If set to None, the PID will compute a new output value every time
            it is called.
        :param output_limits: The initial output limits to use, given as an iterable with 2
            elements, for example: (lower, upper). The output will never go below the lower limit
            or above the upper limit. Either of the limits can also be set to None to have no limit
            in that direction. Setting output limits also avoids integral windup, since the
            integral term will never be allowed to grow outside of the limits.
        :param auto_mode: Whether the controller should be enabled (auto mode) or not (manual mode)
        :param proportional_on_measurement: Whether the proportional term should be calculated on
            the input directly rather than on the error (which is the traditional way). Using
            proportional-on-measurement avoids overshoot for some types of systems.
        :param error_map: Function to transform the error value in another constrained value.
        """
        self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
        self.setpoint = setpoint
        self.sample_time = sample_time

        self._min_output, self._max_output = None, None
        self._auto_mode = auto_mode
        self.proportional_on_measurement = proportional_on_measurement
        self.error_map = error_map

        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._last_time = None
        self._last_output = None
        self._last_input = None

        self.output_limits = output_limits
        self.reset()

    def __call__(self, input_, dt=None):
        """
        Update the PID controller.

        Call the PID controller with *input_* and calculate and return a control output if
        sample_time seconds has passed since the last update. If no new output is calculated,
        return the previous output instead (or None if no value has been calculated yet).

        :param dt: If set, uses this value for timestep instead of real time. This can be used in
            simulations when simulation time is different from real time.
        """
        if not self.auto_mode:
            return self._last_output

        now = time.monotonic()
        if dt is None:
            dt = now - self._last_time if now - self._last_time else 1e-16
        elif dt <= 0:
            raise ValueError(
                'dt has negative value {}, must be positive'.format(dt))

        if self.sample_time is not None and dt < self.sample_time and self._last_output is not None:
            # only update every sample_time seconds
            return self._last_output

        # compute error terms
        error = self.setpoint - input_
        d_input = input_ - (
            self._last_input if self._last_input is not None else input_)

        # check if must map the error
        if self.error_map is not None:
            error = self.error_map(error)

        # compute the proportional term
        if not self.proportional_on_measurement:
            # regular proportional-on-error, simply set the proportional term
            self._proportional = self.Kp * error
        else:
            # add the proportional error on measurement to error_sum
            self._proportional -= self.Kp * d_input

        # compute integral and derivative terms
        self._integral += self.Ki * error * dt
        self._integral = _clamp(self._integral,
                                self.output_limits)  # avoid integral windup

        self._derivative = -self.Kd * d_input / dt

        # compute final output
        output = self._proportional + self._integral + self._derivative
        output = _clamp(output, self.output_limits)

        # keep track of state
        self._last_output = output
        self._last_input = input_
        self._last_time = now

        return output

    def __repr__(self):
        return (
            '{self.__class__.__name__}('
            'Kp={self.Kp!r}, Ki={self.Ki!r}, Kd={self.Kd!r}, '
            'setpoint={self.setpoint!r}, sample_time={self.sample_time!r}, '
            'output_limits={self.output_limits!r}, auto_mode={self.auto_mode!r}, '
            'proportional_on_measurement={self.proportional_on_measurement!r},'
            'error_map={self.error_map!r}'
            ')'
        ).format(self=self)

    @property
    def components(self):
        """
        The P-, I- and D-terms from the last computation as separate components as a tuple. Useful
        for visualizing what the controller is doing or when tuning hard-to-tune systems.
        """
        return self._proportional, self._integral, self._derivative

    @property
    def tunings(self):
        """The tunings used by the controller as a tuple: (Kp, Ki, Kd)."""
        return self.Kp, self.Ki, self.Kd

    @tunings.setter
    def tunings(self, tunings):
        """Set the PID tunings."""
        self.Kp, self.Ki, self.Kd = tunings

    @property
    def auto_mode(self):
        """Whether the controller is currently enabled (in auto mode) or not."""
        return self._auto_mode

    @auto_mode.setter
    def auto_mode(self, enabled):
        """Enable or disable the PID controller."""
        self.set_auto_mode(enabled)

    def set_auto_mode(self, enabled, last_output=None):
        """
        Enable or disable the PID controller, optionally setting the last output value.

        This is useful if some system has been manually controlled and if the PID should take over.
        In that case, disable the PID by setting auto mode to False and later when the PID should
        be turned back on, pass the last output variable (the control variable) and it will be set
        as the starting I-term when the PID is set to auto mode.

        :param enabled: Whether auto mode should be enabled, True or False
        :param last_output: The last output, or the control variable, that the PID should start
            from when going from manual mode to auto mode. Has no effect if the PID is already in
            auto mode.
        """
        if enabled and not self._auto_mode:
            # switching from manual mode to auto, reset
            self.reset()

            self._integral = last_output if last_output is not None else 0
            self._integral = _clamp(self._integral, self.output_limits)

        self._auto_mode = enabled

    @property
    def output_limits(self):
        """
        The current output limits as a 2-tuple: (lower, upper).

        See also the *output_limits* parameter in :meth:`PID.__init__`.
        """
        return self._min_output, self._max_output

    @output_limits.setter
    def output_limits(self, limits):
        """Set the output limits."""
        if limits is None:
            self._min_output, self._max_output = None, None
            return

        min_output, max_output = limits

        if None not in limits and max_output < min_output:
            raise ValueError('lower limit must be less than upper limit')

        self._min_output = min_output
        self._max_output = max_output

        self._integral = _clamp(self._integral, self.output_limits)
        self._last_output = _clamp(self._last_output, self.output_limits)

    def reset(self):
        """
        Reset the PID controller internals.

        This sets each term to 0 as well as clearing the integral, the last output and the last
        input (derivative calculation).
        """
        self._proportional = 0
        self._integral = 0
        self._derivative = 0

        self._integral = _clamp(self._integral, self.output_limits)

        self._last_time = time.monotonic()
        self._last_output = None
        self._last_input = None


class AltitudeRegressionCalculator:
    """
    An abstraction that makes it easier to interact with the polynomial
    function regression.
    """
    a, b, c = -51, 330, -420
    ALPHA = 0.05

    def process_frames(self, data_scan):
        """
        Process the last 2 seconds of data and update the gradient descent accordingly
        @param data_scan: a list of pairs of (time, altitude)
        """
        derivative = sum(
            [(A - (self.a * T ** 1.5 + self.b * T + self.c)) / 2000 for T, A in
             data_scan]) / len(data_scan)
        self.a += self.ALPHA * derivative * sum(
            [(T / 30) ** 1.5 for T, _ in data_scan])
        self.b += self.ALPHA * derivative * sum([T / 30 for T, _ in data_scan])
        self.c += self.ALPHA * derivative

    def get_predicted_apogee(self):
        """
        Automatically calculate the predicted apogee based on the latest regression data
        """
        apogee_time = (-self.b / 1.5 / self.a) ** 2
        return self.a * apogee_time ** 1.5 + self.b * apogee_time + self.c
    #
    # def __repr__(self):
    #     return f"Regression({self.a}, {self.b}, {self.c})"


i2c = I2C(SCL, SDA)
imu = adafruit_bno055.BNO055_I2C(i2c)
bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)

spd = pwmio.PWMOut(D13)
dir = pwmio.PWMOut(D4)
fin_motor = motor.DCMotor(spd, dir)

# Reset the altimeter such that the current altitude is 0 m
bmp.sea_level_pressure = bmp.pressure

# The CircuitPython library for the IMU does not support reading the interrupt status register, so we will manually
# interact with the IMU over i2c. Addresses are from the IMU datasheet
# Enable the high-g interrupt in the INT_EN register
imu._write_register(0x10, 0b00100000)
# Enable the appropriate axis in ACC_INT_Settings register
imu._write_register(0x12, 0b10000000)
# Set a 5g threshold in ACC_HG_THRES
imu._write_register(0x14, 0b00000000)
# Using the default 0x0F value for ACC_HG_DURATION

# Stall until the IMU detects lift-off
while imu._read_register(0x37) != 0b00100000:
    pass

time.sleep(5)  # Step 2: disable fins interfering with motor burn

flight_regression = AltitudeRegressionCalculator()
pid = PID(0.34, 0, 0, setpoint=1609, output_limits=(-1, 1))

launch_time = time.time()
data_scan = []

CALIBRATE_SPEED = 0.1
CALIBRATE_TIME = 10

SAFEST_POSITION = CALIBRATE_SPEED * CALIBRATE_TIME

motor_position = 0
motor_throttle = 0
last_timestamp = time.time()

# simulated_flight_data = [(datum[0], datum[1] * 0.3048) for datum in [
#     [float(datum) for datum in line.split(",") if datum.strip()] for line in
#     open("noFinsADAS1.csv", "r").readlines() if
#     not line.startswith("#") and 18 > float(line.split(",")[0]) > 4
# ]]

while len(data_scan) < 3 or data_scan[-1][1] < bmp.altitude:
# while True:
    current_time = time.time() - launch_time
    data_scan = [(T, A) for T, A in data_scan if T >= current_time - 2] + [
        (current_time, bmp.altitude)
    ]  # TODO opportunity for optimization
    # data_scan = simulated_flight_data

    flight_regression.process_frames(data_scan)

    predicted_apogee = flight_regression.get_predicted_apogee()
    output = pid(predicted_apogee)

    delta_time = time.time() - last_timestamp
    motor_position += motor_throttle * delta_time

    future_position = motor_position + output * delta_time * 1.15
    if future_position < 0 or future_position > SAFEST_POSITION:
        motor_throttle = 0
    else:
        motor_throttle = output

    fin_motor.throttle = motor_throttle

    last_timestamp = time.time()
