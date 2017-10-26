#
# Race Capture App
#
# Copyright (C) 2014-2017 Autosport Labs
#
# This file is part of the Race Capture App
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details. You should
# have received a copy of the GNU General Public License along with
# this code. If not, see <http://www.gnu.org/licenses/>.

import traceback
import threading
import multiprocessing
from Queue import Empty
from time import sleep
from kivy.logger import Logger
from autosportlabs.comms.commscommon import PortNotOpenException

STAY_ALIVE_TIMEOUT = 4
COMMAND_CLOSE = 'CLOSE'
COMMAND_KEEP_ALIVE = 'PING'

def connection_process_message_reader(rx_queue, connection, should_run):
    Logger.debug('Comms: connection process message reader started')

    while should_run.is_set():
        try:
            msg = connection.read_line()
            if msg:
                rx_queue.put(msg)
        except:
            Logger.error('Comms: Exception in connection_process_message_reader')
            Logger.debug(traceback.format_exc())
            should_run.clear()
            sleep(0.5)
    Logger.debug('Comms: connection process message reader exited')

def connection_process_message_writer(tx_queue, connection, should_run):
    Logger.debug('Comms: connection process message writer started')
    while should_run.is_set():
        try:
            message = tx_queue.get(True, 1.0)
            if message:
                connection.write(message)
        except Empty:
            pass
        except Exception as e:
            Logger.error('Comms: Exception in connection_process_message_writer ' + str(e))
            Logger.debug(traceback.format_exc())
            should_run.clear()
            sleep(0.5)
    Logger.debug('Comms: connection process message writer exited')

def connection_message_process(connection, device, rx_queue, tx_queue, command_queue):
    Logger.debug('Comms: connection process starting')

    try:
        connection.open(device)
        connection.flushInput()
        connection.flushOutput()

        reader_writer_should_run = threading.Event()
        reader_writer_should_run.set()

        reader_thread = threading.Thread(target=connection_process_message_reader, args=(rx_queue, connection, reader_writer_should_run))
        reader_thread.start()

        writer_thread = threading.Thread(target=connection_process_message_writer, args=(tx_queue, connection, reader_writer_should_run))
        writer_thread.start()


        while reader_writer_should_run.is_set():
            try:
                command = command_queue.get(True, STAY_ALIVE_TIMEOUT)
                if command == COMMAND_CLOSE:
                    Logger.debug('Comms: connection process: got close command')
                    reader_writer_should_run.clear()
            except Empty:
                Logger.debug('Comms: keep alive timeout')
                reader_writer_should_run.clear()
        Logger.debug('Comms: connection worker exiting')

        reader_thread.join()
        writer_thread.join()

        try:
            connection.close()
        except:
            Logger.debug('Comms: Exception closing connection worker connection')
            Logger.debug(traceback.format_exc())
    except Exception as e:
        Logger.debug('Comms: Exception setting up connection process: ' + str(type(e)) + str(e))
        Logger.trace(traceback.format_exc())

    Logger.debug('Comms: connection worker exited')


class Comms():
    CONNECT_TIMEOUT = 1.0
    DEFAULT_TIMEOUT = 1.0
    QUEUE_FULL_TIMEOUT = 1.0
    _timeout = DEFAULT_TIMEOUT
    device = None
    _connection = None
    _connection_process = None
    _rx_queue = None
    _tx_queue = None
    _command_queue = None

    def __init__(self, device, connection):
        self.device = device
        self._connection = connection
        self.supports_streaming = False

    def start_connection_process(self):
        rx_queue = multiprocessing.Queue()
        tx_queue = multiprocessing.Queue(5)
        command_queue = multiprocessing.Queue()
        connection_process = multiprocessing.Process(target=connection_message_process, args=(self._connection, self.device, rx_queue, tx_queue, command_queue))
        connection_process.start()
        self._rx_queue = rx_queue
        self._tx_queue = tx_queue
        self._command_queue = command_queue
        self._connection_process = connection_process

    def get_available_devices(self):
        return self._connection.get_available_devices()

    def isOpen(self):
        return self._connection_process != None and self._connection_process.is_alive()

    def open(self):
        connection = self._connection
        Logger.debug('Comms: Opening connection ' + str(self.device))
        self.start_connection_process()

    def keep_alive(self):
        try:
            self._command_queue.put_nowait(COMMAND_KEEP_ALIVE)
        except:
            pass

    def close(self):
        Logger.debug('Comms: comms.close()')
        if self.isOpen():
            try:
                Logger.debug('Comms: closing connection process')
                self._command_queue.put_nowait(COMMAND_CLOSE)
                self._connection_process.join(self._timeout * 2)
                Logger.debug('Comms: connection process joined')
            except:
                Logger.error('Comms: Timeout joining connection process')

    def read_message(self):
        if not self.isOpen():
            raise PortNotOpenException('Port Closed')
        try:
            return self._rx_queue.get(True, self._timeout)
        except:  # returns Empty object if timeout is hit
            return None

    def write_message(self, message):
        if not self.isOpen(): raise PortNotOpenException('Port Closed')
        self._tx_queue.put(message, True, Comms.QUEUE_FULL_TIMEOUT)

    def is_wireless(self):
        """Returns if this comms object uses wireless communications or not.
        :return: False
        """
        return False
