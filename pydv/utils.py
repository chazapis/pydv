# Copyright (C) 2018 Antony Chazapis SV9OAN
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

def or_valueerror(condition):
    if not condition:
        raise ValueError

def pad(s, count, padding='\x00'):
    return s + ((count - len(s)) * padding)

def resolve(host):
    import socket

    try:
        socket.inet_aton(host)
        return host
    except socket.error:
        pass

    try:
        return socket.gethostbyname(host)
    except:
        raise ValueError

# Based on: https://www.oreilly.com/library/view/python-cookbook/0596001673/ch06s03.html

import threading

class StoppableThread(threading.Thread):
    def __init__(self, name='StoppableThread'):
        self._stop_event = threading.Event()
        self._sleep_period = 1.0

        threading.Thread.__init__(self, name=name)

    def loop(self):
        raise NotImplementedError

    def run(self):
        while not self._stop_event.isSet():
            self.loop()
            self._stop_event.wait(self._sleep_period)

    def join(self, timeout=None):
        self._stop_event.set()
        threading.Thread.join(self, timeout)
