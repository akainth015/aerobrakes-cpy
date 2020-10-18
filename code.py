
import os
import board
import digitalio
import time
import busio
import adafruit_bno055

#modules to access SD card and filesystem
import adafruit_sdcard
import storage
from digitalio import DigitalInOut, Direction

#needed for the motor
import pulseio
from adafruit_motor import servo, motor

spd = pulseio.PWMOut(board.D13)
spd.duty_cycle = 0
dir_pin = DigitalInOut(board.D4)
dir_pin.direction = Direction.OUTPUT

#spd.duty_cycle = 0

#initialize connection between imu and microcontroller
i2c = busio.I2C(board.SCL, board.SDA)
#i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)

sensor = adafruit_bno055.BNO055(i2c)

#spi bus to write and read data from SD card
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

#chip select output, pin 12 for adafruit
cs = digitalio.DigitalInOut(board.D12)

#create microSD card object and filesystem object
sdcard = adafruit_sdcard.SDCard(spi, cs)
vfs = storage.VfsFat(sdcard)

#mount sdcard filesystem into circuitpython filesystem
storage.mount(vfs, "/sd")

fins_deployed = False
fins_retracted = False
launch_detected = False

with open("/sd/adas.txt", "a") as f:
    f.write('{:5}'.format('#'))
    f.write('{:10}'.format('Temp'))
    f.write('{:10}'.format('AccX'))
    f.write('{:10}'.format('AccY'))
    f.write('{:10}'.format('AccZ'))
    f.write('{:10}'.format('MagX'))
    f.write('{:10}'.format('MagY'))
    f.write('{:10}'.format('MagZ'))
    f.write('{:10}'.format('GyroX'))
    f.write('{:10}'.format('GyroY'))
    f.write('{:10}'.format('GyroZ'))
    f.write('{:10}'.format('EulerX'))
    f.write('{:10}'.format('EulerY'))
    f.write('{:10}'.format('EulerZ'))
    f.write('{:10}'.format('Quat1'))
    f.write('{:10}'.format('Quat2'))
    f.write('{:10}'.format('Quat3'))
    f.write('{:10}'.format('Quat4'))
    f.write('{:10}'.format('LAccX'))
    f.write('{:10}'.format('LAccY'))
    f.write('{:10}'.format('LAccZ'))
    f.write('{:10}'.format('GravX'))
    f.write('{:10}'.format('GravY'))
    f.write('{:10}'.format('GravZ'))
    f.write('\n')
i = 1

while True:
    with open("/sd/adas.txt", "a") as f:
        t = sensor.temperature
        c = sensor.calibrated
        g = sensor.gravity

            #f.write(str(t))
            #f.write(str(c))
            #f.write(str(g))
        f.write('{:<5d}'.format(i))
        f.write('{:<10.5f}'.format(sensor.temperature))
        f.write('{:<10.5f}'.format(sensor.acceleration[0]))
        f.write('{:<10.5f}'.format(sensor.acceleration[1]))
        f.write('{:<10.5f}'.format(sensor.acceleration[2]))
        f.write('{:<10.5f}'.format(sensor.magnetic[0]))
        f.write('{:<10.5f}'.format(sensor.magnetic[1]))
        f.write('{:<10.5f}'.format(sensor.magnetic[2]))
        f.write('{:<10.5f}'.format(sensor.gyro[0]))
        f.write('{:<10.5f}'.format(sensor.gyro[1]))
        f.write('{:<10.5f}'.format(sensor.gyro[2]))
        f.write('{:<10.5f}'.format(sensor.euler[0]))
        f.write('{:<10.5f}'.format(sensor.euler[1]))
        f.write('{:<10.5f}'.format(sensor.euler[2]))
        f.write('{:<10.5f}'.format(sensor.quaternion[0]))
        f.write('{:<10.5f}'.format(sensor.quaternion[1]))
        f.write('{:<10.5f}'.format(sensor.quaternion[2]))
        f.write('{:<10.5f}'.format(sensor.quaternion[3]))
        f.write('{:<10.5f}'.format(sensor.linear_acceleration[0]))
        f.write('{:<10.5f}'.format(sensor.linear_acceleration[1]))
        f.write('{:<10.5f}'.format(sensor.linear_acceleration[2]))
        f.write('{:<10.5f}'.format(sensor.gravity[0]))
        f.write('{:<10.5f}'.format(sensor.gravity[1]))
        f.write('{:<10.5f}'.format(sensor.gravity[2]))
        f.write('\n')
        i = i + 1

        # f.write('Temperature: {} degrees C'.format(sensor.temperature))
        # f.write('\n\n')
        # f.write('Accelerometer (m/s^2): {}'.format(sensor.acceleration))
        # f.write('\n\n')
        # f.write('Magnetometer (microteslas): {}'.format(sensor.magnetic))
        # f.write('\n\n')
        # f.write('Gyroscope (rad/sec): {}'.format(sensor.gyro))
        # f.write('\n\n')
        # f.write('Euler angle: {}'.format(sensor.euler))
        # f.write('\n\n')
        # f.write('Quaternion: {}'.format(sensor.quaternion))
        # f.write('\n\n')
        # f.write('Linear acceleration (m/s^2): {}'.format(sensor.linear_acceleration))
        # f.write('\n\n')
        # f.write('Gravity (m/s^2): {}'.format(sensor.gravity))
        # f.write('\n\n\n')

    if sensor.linear_acceleration[2] > 50:
        launch_detected = True

    #if (not fins_deployed) and launch_detected and sensor.linear_acceleration[2] < 5:
    #if (not fins_retracted) and sensor.linear_acceleration[2] < 1:
        '''spd.duty_cycle = 6000
        time.sleep(1)
        fins_deployed = True
        print("1")
        spd.duty_cycle = 0
        time.sleep(10)
        dir_pin.value = not dir_pin.value
        spd.duty_cycle = 6000
        time.sleep(2)
        fins_retracted = True
        spd.duty_cycle = 0 '''

    # time.sleep(60)
    # spd.duty_cycle = 6000
    # fins_deployed = True
    # print("1")
    # spd.duty_cycle = 0
    # time.sleep(10)
    # dir_pin.value = not dir_pin.value
    # spd.duty_cycle = 6000
    # time.sleep(2)
    # fins_retracted = True




    #if fins_deployed and (not fins_retracted) and sensor.linear_acceleration[2] < 2:
    #if fins_deployed and (not fins_retracted) and sensor.linear_acceleration[2] < 1:
        #dir_pin.value = not dir_pin.value
        #spd.duty_cycle = 6000
        #time.sleep(2)
        #fins_retracted = True
        #print("2")
        #spd.duty_cycle = 0


    #with open("/sd/adas.txt", "r") as f:
        #lines = f.readlines()
        #for line in lines:
            #print(line)

    time.sleep(2)