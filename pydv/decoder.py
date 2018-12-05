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

import pydv.mbelib

def dv_decoder():
    states = []
    for i in range(10):
        s = pydv.mbelib.init_state()
        pydv.mbelib.set_uvquality(s, i)
        states.append(s)

    for i in range(10):
        print pydv.mbelib.get_uvquality(states[i])

    print states

def main():
    dv_decoder()

if __name__ == '__main__':
    dv_decoder()
