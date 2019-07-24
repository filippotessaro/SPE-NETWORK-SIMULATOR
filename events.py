# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2016 Michele Segata <segata@ccs-labs.org>


class Events:
    """
    Defines event types for the simulation
    """

    # start transmission event
    START_TX = 0
    # end transmission event
    END_TX = 1
    # start reception event
    START_RX = 2
    # end reception event
    END_RX = 3
    # packet arrival event
    PACKET_ARRIVAL = 4
    # end of processing after reception or transmission. can start operations
    # again
    END_PROC = 5
    # timeout for RX state avoiding getting stuck into RX indefinitely
    RX_TIMEOUT = 6
