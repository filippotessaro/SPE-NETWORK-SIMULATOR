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

import sys
from module import Module
from distribution import Distribution
from event import Event
from events import Events
from packet import Packet


class Node(Module):
    """
    This class implements a node capable of communicating with other devices
    """

    # transmission speed parameter (bits per second)
    DATARATE = "datarate"
    # queue size
    QUEUE = "queue"
    # inter-arrival distribution (seconds)
    INTERARRIVAL = "interarrival"
    # packet size distribution (bytes)
    SIZE = "size"
    # processing time distribution (seconds)
    PROC_TIME = "processing"
    # max packet size (bytes)
    MAXSIZE = "maxsize"

    # list of possible states for this node
    IDLE = 0
    TX = 1
    RX = 2
    PROC = 3

    def __init__(self, config, channel, x, y):
        """
        Constructor.
        :param config: the set of configs loaded by the simulator
        :param channel: the channel to which frames are sent
        :param x: x position
        :param y: y position
        """
        Module.__init__(self)
        # load configuration parameters
        self.datarate = config.get_param(Node.DATARATE)
        self.queue_size = config.get_param(Node.QUEUE)
        self.interarrival = Distribution(config.get_param(Node.INTERARRIVAL))
        self.size = Distribution(config.get_param(Node.SIZE))
        self.proc_time = Distribution(config.get_param(Node.PROC_TIME))
        self.maxsize = config.get_param(Node.MAXSIZE)
        # queue of packets to be sent
        self.queue = []
        # current state
        self.state = Node.IDLE
        self.logger.log_state(self, Node.IDLE)
        # save position
        self.x = x
        self.y = y
        # save channel
        self.channel = channel
        # current packet being either sent or received
        self.current_pkt = None
        # count the number of frames currently under reception
        self.receiving_count = 0
        # timeout event used to avoid being stuck in the RX state
        self.timeout_event = None
        # timeout time for the rx timeout event. set as the time needed to
        # transmit a packet of the maximum size plus a small amount of 10
        # microseconds
        self.timeout_time = self.maxsize * 8.0 / self.datarate + 10e-6

    def initialize(self):
        """
        Initialization. Starts node operation by scheduling the first packet
        """
        self.schedule_next_arrival()

    def handle_event(self, event):
        """
        Handles events notified to the node
        :param event: the event
        """
        if event.get_type() == Events.PACKET_ARRIVAL:
            self.handle_arrival()
        elif event.get_type() == Events.START_RX:
            self.handle_start_rx(event)
        elif event.get_type() == Events.END_RX:
            self.handle_end_rx(event)
        elif event.get_type() == Events.END_TX:
            self.handle_end_tx(event)
        elif event.get_type() == Events.END_PROC:
            self.handle_end_proc(event)
        elif event.get_type() == Events.RX_TIMEOUT:
            self.handle_rx_timeout(event)
        else:
            print("Node %d has received a notification for event type %d which"
                  " can't be handled", (self.get_id(), event.get_type()))
            sys.exit(1)

    def schedule_next_arrival(self):
        """
        Schedules a new arrival event
        """
        # extract random value for next arrival
        arrival = self.interarrival.get_value()
        # generate an event setting this node as destination
        event = Event(self.sim.get_time() + arrival, Events.PACKET_ARRIVAL,
                      self, self)
        self.sim.schedule_event(event)

    def handle_arrival(self):
        """
        Handles a packet arrival
        """
        # draw packet size from the distribution
        packet_size = self.size.get_value()
        # log the arrival
        self.logger.log_arrival(self, packet_size)
        if self.state == Node.IDLE:
            # if we are in a idle state, then there must be no packets in the
            # queue
            assert(len(self.queue) == 0)
            # if current state is IDLE and there are no packets in the queue, we
            # can start transmitting
            self.transmit_packet(packet_size)
            self.state = Node.TX
            self.logger.log_state(self, Node.TX)
        else:
            # if we are either transmitting or receiving, packet must be queued
            if self.queue_size == 0 or len(self.queue) < self.queue_size:
                # if queue size is infinite or there is still space
                self.queue.append(packet_size)
                self.logger.log_queue_length(self, len(self.queue))
            else:
                # if there is no space left, we drop the packet and log
                self.logger.log_queue_drop(self, packet_size)
        # schedule next arrival
        self.schedule_next_arrival()

    def handle_start_rx(self, event):
        """
        Handles beginning of a frame reception
        :param event: the RX event including the frame being received
        """
        new_packet = event.get_obj()
        if self.state == Node.IDLE:
            if self.receiving_count == 0:
                # node is idle: it will try to receive this packet
                assert(self.current_pkt is None)
                new_packet.set_state(Packet.PKT_RECEIVING)
                self.current_pkt = new_packet
                self.state = Node.RX
                assert(self.timeout_event is None)
                # create and schedule the RX timeout
                self.timeout_event = Event(self.sim.get_time() +
                                           self.timeout_time, Events.RX_TIMEOUT,
                                           self, self, None)
                self.sim.schedule_event(self.timeout_event)
                self.logger.log_state(self, Node.RX)
            else:
                # there is another signal in the air but we are IDLE. this
                # happens if we start receiving a frame while transmitting
                # another. when we are done with the transmission we assume we
                # are not able to detect that there is another frame in the air
                # (we are not doing carrier sensing). In this case we assume we
                # are not able to detect the new one and set that to corrupted
                new_packet.set_state(Packet.PKT_CORRUPTED)
        else:
            # node is either receiving or transmitting
            if self.state == Node.RX and self.current_pkt is not None:
                # the frame we are currently receiving is corrupted by a
                # collision, if we have one
                self.current_pkt.set_state(Packet.PKT_CORRUPTED)
            # the same holds for the new incoming packet. either if we are in
            # the RX, TX, or PROC state, we won't be able to decode it
            new_packet.set_state(Packet.PKT_CORRUPTED)
        # in any case, we schedule a new event to handle the end of this frame
        end_rx = Event(self.sim.get_time() + new_packet.get_duration(),
                       Events.END_RX, self, self, new_packet)
        self.sim.schedule_event(end_rx)
        # count this as currently being received
        self.receiving_count = self.receiving_count + 1

    def handle_end_rx(self, event):
        """
        Handles the end of a reception
        :param event: the END_RX event
        """
        packet = event.get_obj()
        # if the packet that ends is the one that we are trying to receive, but
        # we are not in the RX state, then something is very wrong
        if self.current_pkt is not None and \
           packet.get_id() == self.current_pkt.get_id():
            assert(self.state == Node.RX)
        if self.state == Node.RX:
            if packet.get_state() == Packet.PKT_RECEIVING:
                # the packet is not in a corrupted state: we succesfully
                # received it
                packet.set_state(Packet.PKT_RECEIVED)
                # just to be sure: we can only correctly receive the packet we
                # were trying to decode
                assert(packet.get_id() == self.current_pkt.get_id())
            # we might be in RX state but have no current packet. this can
            # happen when a packet overlaps with the current one being received
            # and the one being received terminates earlier. we assume to stay
            # in the RX state because we are not able to detect the end of the
            # frame
            if self.current_pkt is not None and \
               packet.get_id() == self.current_pkt.get_id():
                self.current_pkt = None
            if self.receiving_count == 1:
                # this is the only frame currently in the air, move to PROC
                # before restarting operations
                self.switch_to_proc()
                # delete the timeout event
                self.sim.cancel_event(self.timeout_event)
                self.timeout_event = None
        self.receiving_count = self.receiving_count - 1
        # log packet
        self.logger.log_packet(event.get_source(), self, packet)

    def switch_to_proc(self):
        """
        Switches to the processing state and schedules the end_proc event
        """
        proc_time = self.proc_time.get_value()
        proc = Event(self.sim.get_time() + proc_time, Events.END_PROC, self,
                     self)
        self.sim.schedule_event(proc)
        self.state = Node.PROC
        self.logger.log_state(self, Node.PROC)

    def handle_rx_timeout(self, event):
        """
        Handles RX timeout
        :param event: the RX_TIMEOUT event
        """
        # when this event happens, we can only be in RX state, otherwise
        # something is wrong
        assert(self.state == Node.RX)
        # in addition, the timeout should be longer than any possible packet,
        # meaning that we must not be receiving a packet when the timeout occurs
        assert(self.current_pkt is None)
        # the timeout forces us to switch to the PROC state
        self.switch_to_proc()
        self.timeout_event = None

    def handle_end_tx(self, event):
        """
        Handles the end of a transmission done by this node
        :param event: the END_TX event
        """
        assert(self.state == Node.TX)
        assert(self.current_pkt is not None)
        assert(self.current_pkt.get_id() == event.get_obj().get_id())
        self.current_pkt = None
        # the only thing to do here is to move to the PROC state
        self.switch_to_proc()

    def handle_end_proc(self, event):
        """
        Handles the end of the processing period, resuming operations
        :param event: the END_PROC event
        """
        assert(self.state == Node.PROC)
        if len(self.queue) == 0:
            # resuming operations but nothing to transmit. back to IDLE
            self.state = Node.IDLE
            self.logger.log_state(self, Node.IDLE)
        else:
            # there is a packet ready, trasmit it
            packet_size = self.queue.pop(0)
            self.transmit_packet(packet_size)
            self.state = Node.TX
            self.logger.log_state(self, Node.TX)
            self.logger.log_queue_length(self, len(self.queue))

    def transmit_packet(self, packet_size):
        """
        Generates, sends, and schedules end of transmission of a new packet
        :param packet_size: size of the packet to send in bytes
        """
        assert(self.current_pkt is None)
        duration = packet_size * 8 / self.datarate
        # transmit packet
        packet = Packet(packet_size, duration)
        self.channel.start_transmission(self, packet)
        # schedule end of transmission
        end_tx = Event(self.sim.get_time() + duration, Events.END_TX, self,
                       self, packet)
        self.sim.schedule_event(end_tx)
        self.current_pkt = packet

    def get_posx(self):
        """
        Returns x position
        :returns: x position in meters
        """
        return self.x

    def get_posy(self):
        """
        Returns y position
        :returns: y position in meters
        """
        return self.y
