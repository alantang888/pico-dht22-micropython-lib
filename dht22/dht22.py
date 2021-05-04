import utime
from machine import Pin
from utime import *
from math import fabs
from rp2 import asm_pio, StateMachine, PIO

_irq_count = 0
temp_data = bytearray([0 for i in range(5)])

EIGHT_1_BIT_MASK = const(0b11111111)
SEVEN_1_BIT_MASK = const(0b01111111)


@asm_pio(set_init=PIO.OUT_HIGH, autopush=True, push_thresh=8)
def dht_get_data():
    # wait for sm.put() to trigger run. Otherwise keep waiting
    pull()
    # y use to count byte
    set(y, 4)
    # wait for 8 more loop (when x reach 0, it still have one more execute, x-- happen after jmp compare)
    set(x, 7)
    set(pindirs, 1)
    # send init signal, and wait 9 cycle, total 10 cycle
    set(pins, 0)[9]
    label('init_wait_loop')
    # nop 1 cycle, then wait 8 cycle, jump also take 1 cycle, so total 10 cycle
    nop()[8]
    jmp(x_dec, 'init_wait_loop')
    
    # wait for init response
    set(pindirs, 0)
    wait(1, pin, 0)
    wait(0, pin, 0)
    wait(1, pin, 0)
    
    # start read sensor data
    label('receive_new_byte')
    set(x, 7)
    label('receive_new_bit')
    wait(0, pin, 0)
    # When pin is high then wait 2 more cycle (3 in total). So after 30 us, directly put pin's value to ISR
    wait(1, pin, 0)[2]
    in_(pins, 1)
    jmp(x_dec, 'receive_new_bit')
    # Already received 8 bits, so trigger IRQ to read FIFO data. And start receive new byte
    irq(rel(0))
    jmp(y_dec, 'receive_new_byte')
    # Set pin to output & high. Let data pin keep in high. Then init signal low can trigger data fetch
    set(pindirs, 1)
    set(pins, 1)


def handle_dht_irq(sm):
    global _irq_count, temp_data
    temp_data[_irq_count] = (sm.get())
    _irq_count += 1


class DHT(object):
    def __init__(self, pin: Pin, state_machine_id: int = 0, min_interval: int = 2000):
        """
        Create a DHT object to get communication and get data from DHT sensor.
        :param pin: Pin connected to DHT's data pin
        :param state_machine_id: State Machine ID, default value 1
        :param min_interval: Minimum interval between communication with DHT, default value 2000 (for DHT22)
        :type pin: machine.Pin
        :type state_machine_id: int
        :type min_interval: int
        """
        self._pin = pin
        self._last_pull_time = None
        self._temperature = None
        self._humidity = None
        self._min_interval = min_interval
        # 1 cycle should be 10 us, 1s = 1,000,000us so freq should be 100,000
        self._sm = StateMachine(state_machine_id, dht_get_data, freq=100000, set_base=pin)
        self._sm.irq(handle_dht_irq)
        self._sm.active(1)
    
    def _get_data_from_sensor(self, force: bool = False):
        if force or self._last_pull_time is None or \
                fabs(ticks_diff(ticks_ms(), self._last_pull_time)) > self._min_interval:
            global _irq_count, temp_data
            _irq_count = 0
            for i in range(5):
                temp_data[i] = 0
            
            # start state machine
            self._sm.put(0)
            
            # Wait for state machine work
            utime.sleep_ms(20)
            
            if _irq_count != 5:
                print("Didn't receive enough data. Received {} byte(s).".format(len(temp_data)))
                return
            
            # data validation, 1st byte + 2nd byte + 3rd byte + 4th byte == 5th byte (last 8 bits)
            check_sum = (temp_data[0] + temp_data[1] + temp_data[2] + temp_data[3]) & EIGHT_1_BIT_MASK
            if check_sum != temp_data[4]:
                print('Data validation error.')
                return
            
            # temperature data is last 15 bits, first bit if 1, is negative. data is 10x of actual value
            raw_temperature = ((temp_data[2] & SEVEN_1_BIT_MASK) << 8) + temp_data[3]
            self._temperature = raw_temperature / 10
            if temp_data[2] >> 7 == 1:
                self._temperature *= -1
            
            raw_humidity = (temp_data[0] << 8) + temp_data[1]
            # humidity data is 10x of actual value
            self._humidity = raw_humidity / 10
            
            self._last_pull_time = ticks_ms()
    
    def get_temperature(self, force: bool = False) -> float:
        """
        Get temperature from DHT
        :param force: Force communicate with DHT sensor
        :type force: bool
        :return: Last measured temperature
        :rtype: float
        """
        self._get_data_from_sensor(force)
        return self._temperature
    
    def get_humidity(self, force: bool = False) -> float:
        """
        Get humidity from DHT
        :param force: Force communicate with DHT sensor
        :type force: bool
        :return: Last measured humidity
        :rtype: float
        """
        self._get_data_from_sensor(force)
        return self._humidity
    
    def get_temperature_and_humidity(self, force: bool = False) -> (float, float):
        """
        Get temperature and humidity from DHT
        :param force: Force communicate with DHT sensor
        :type force: bool
        :return: Last measured temperature and humidity
        :rtype: (float, float)
        """
        self._get_data_from_sensor(force)
        return self._temperature, self._humidity
