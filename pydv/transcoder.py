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

import os
import sys
import argparse
import logging

from time import sleep

from dstar import DSTARCallsign
from ambed import AMBEdCodec, AMBEdFrameInPacket, AMBEdFrameOutPacket, AMBEdConnection
from stream import DisconnectedError, DVHeaderPacket, DVFramePacket
from network import NetworkAddress
from dvtool import DVToolFile

def dv_transcoder():
    parser = argparse.ArgumentParser(description='D-STAR transcoder. Connects to an AMBEd server to transcode recordings.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('callsign', help='your callsign')
    parser.add_argument('address', help='AMBEd\'s hostname or IP address')
    parser.add_argument('input', help='name of file to transcode (DVTool format)')
    parser.add_argument('output', help='name of file to write (DVTool format)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(os.path.basename(sys.argv[0]))

    try:
        callsign = DSTARCallsign(args.callsign)
        address = NetworkAddress(args.address, AMBEdConnection.DEFAULT_PORT)
    except ValueError:
        parser.print_help()
        sys.exit(1)

    try:
        with DVToolFile(args.input) as f:
            stream = f.read()
    except Exception as e:
        raise
        logger.error(str(e))
        sys.exit(1)

    header = stream[0]
    if not isinstance(header, DVHeaderPacket):
        logger.error('first packet in stream is not a header')
        sys.exit(1)

    # Determine vocoder (SV9OAN extension)
    version = header.dstar_header.flag_3 & 0xff
    if version == 0:
        codec_in = AMBEdCodec.AMBEPLUS
        codec_out = AMBEdCodec.CODEC2_3200
        header.dstar_header.flag_3 = 0x01
        logger.info('stream encoded with AMBE vocoder')
    elif version & 0x03 == 0x01:
        codec_in = AMBEdCodec.CODEC2_3200
        codec_out = AMBEdCodec.AMBEPLUS
        header.dstar_header.flag_3 = 0
        logger.info('stream encoded with Codec 2 vocoder (mode: 3200, fec: off)')
    elif version & 0x03 == 0x03:
        codec_in = AMBEdCodec.CODEC2_2400
        codec_out = AMBEdCodec.AMBEPLUS
        header.dstar_header.flag_3 = 0
        logger.info('stream encoded with Codec 2 vocoder (mode: 2400, fec: on)')
    else:
        logger.error('unrecognized flag in stream header')
        sys.exit(1)

    try:
        with AMBEdConnection(callsign, address) as conn:
            try:
                with conn.get_stream(codec_in) as transcoder:
                    # Send it all, as AMBEd requires several packets available
                    # before starting to send to the hardware devices.
                    # Replies will be buffered in the stream's incoming queue anyway.
                    for packet in stream:
                        if not isinstance(packet, DVFramePacket):
                            continue
                        frame_in = AMBEdFrameInPacket(packet.packet_id, codec_in, packet.dstar_frame.dvcodec)
                        transcoder.write(frame_in)
                        sleep(0.02)

                    for packet in stream:
                        if not isinstance(packet, DVFramePacket):
                            continue
                        frame_out = transcoder.read()
                        if not isinstance(frame_out, AMBEdFrameOutPacket):
                            # raise ValueError('not enough transcoded frames')
                            break
                        packet.dstar_frame.dvcodec = frame_out.data1 if frame_out.codec1 == codec_out else frame_out.data2
            except (DisconnectedError, KeyboardInterrupt):
                pass
            else:
                with DVToolFile(args.output) as f:
                    f.write(stream)
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

def main():
    dv_transcoder()

if __name__ == '__main__':
    dv_transcoder()
