if __name__ == '__main__':
    import dht22
    from machine import Pin
    from utime import sleep
    
    sleep(2)
    dht_pin = Pin(0)
    d = dht22.DHT(dht_pin)
    while True:
        print('Temperature: {}. Humidity: {}'.format(d.get_temperature(), d.get_humidity()))
        sleep(2)
