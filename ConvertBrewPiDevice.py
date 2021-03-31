#!/usr/bin/env python3

import serial
import serial.tools.list_ports
from pprint import pprint as pp  # DEBUG


class ConvertBrewPiDevice:
    """ ConvertBrewPiPorts class converts between BrewPi and system device information. """

    def __init__(self):
        self.brewpi_tty = None
        self.device = None
        self.serial_number = None

    def get_device_from_brewpidev(self, brewpi_tty):
        self.brewpi_tty = brewpi_tty
        if self.brewpi_tty and self.brewpi_tty is not None:
            port_list = serial.tools.list_ports.comports(True)
            for port in port_list:
                if port.device == self.brewpi_tty:
                    hwid = port.hwid.split()
                    self.device = hwid[0].split("=")[1]
        return self.device

    def get_device_from_serial_number(self, serial_number):
        self.serial_number = serial_number
        if self.serial_number and self.serial_number is not None:
            port_list = serial.tools.list_ports.comports()
            for port in port_list:
                if port.serial_number == self.serial_number:
                    self.device = port.device
        return self.device

    def get_serial_number_from_device(self, device):
        self.device = device
        if self.device and self.device is not None:
            port_list = serial.tools.list_ports.comports()
            for port in port_list:
                if port.device == self.device:
                    self.serial_number = port.serial_number
        return self.serial_number

    def get_serial_number_from_brewpidev(self, brewpi_tty):
        self.brewpi_tty = brewpi_tty
        if self.brewpi_tty and self.brewpi_tty is not None:
            port_list = serial.tools.list_ports.comports(True)
            for port in port_list:
                if port.device == self.brewpi_tty:
                    hwid = port.hwid.split()
                    self.device = hwid[0].split("=")[1]
        if self.device and self.device is not None:
            port_list = serial.tools.list_ports.comports()
            for port in port_list:
                if port.device == self.device:
                    self.serial_number = port.serial_number
        return self.serial_number

    def get_brewpidev_from_serial_number(self, serial_number):
        self.serial_number = serial_number
        if self.serial_number and self.serial_number is not None:
            port_list = serial.tools.list_ports.comports()
            for port in port_list:
                if port.serial_number == self.serial_number:
                    self.device = port.device
        if self.device and self.device is not None:
            port_list = serial.tools.list_ports.comports(True)
            try:
                hwid = port.hwid.split()
                if hwid[0].split("=")[1] == self.device:
                    self.brewpi_tty == port.device
            except:
                pass
        return self.brewpi_tty

    def get_brewpidev_from_device(self, device):
        self.device = device
        if self.device and self.device is not None:
            port_list = serial.tools.list_ports.comports(True)
            try:
                hwid = port.hwid.split()
                if hwid[0].split("=")[1] == self.device:
                    self.brewpi_tty == port.device
            except:
                pass
        return self.brewpi_tty


if __name__ == '__main__':
    convert = ConvertBrewPiDevice()
    print("DEBUG: get_device_from_brewpidev(/dev/brewpi1): {}".format(
        convert.get_device_from_brewpidev("/dev/brewpi1")))
    print("DEBUG: get_device_from_serial_number(95433343933351C07232): {}".format(
        convert.get_device_from_serial_number("95433343933351C07232")))

    print("DEBUG: get_serial_number_from_device(/dev/ttyACM0): {}".format(
        convert.get_serial_number_from_device("/dev/ttyACM0")))
    print("DEBUG: get_serial_number_from_brewpidev(/dev/brewpi1): {}".format(
        convert.get_serial_number_from_brewpidev("/dev/brewpi1")))

    print("DEBUG: get_brewpidev_from_serial_number(95433343933351C07232): {}".format(
        convert.get_brewpidev_from_serial_number("95433343933351C07232")))
    print("DEBUG: get_brewpidev_from_device(/dev/ttyACM0): {}".format(
        convert.get_brewpidev_from_device("/dev/ttyACM0")))
