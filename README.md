# DHT22 Library for Raspberry Pico with MicroPython

This library only work with Raspberry Pico. 
Because it's using Pico's PIO and State Machine to communication with DHT sensor. 
Since MicroPython on Pico should not fast enough to communication with DHT. 

It only tested with DHT22, I don't have DHT11. So not sure is it work. (On datasheet look like should work.)

Example: [dht22/main.py](dht22/main.py)

I understand I reinventing the wheel again. This just for me understand some basic Pico PIO.
