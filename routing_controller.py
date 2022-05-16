# The program implements a simple controller for a network with 6 hosts and 5 switches.
# The switches are connected in a diamond topology (without vertical links):
#    - 3 hosts are connected to the left (s1) and 3 to the right (s5) edge of the diamond.
# Overall operation of the controller:
#    - default routing is set in all switches on the reception of packet_in messages form the switch,
#    - then the routing for (h1-h4) pair in switch s1 is changed every one second in a round-robin manner to load balance the traffic through switches s3, s4, s2.


from json import load
from turtle import pos
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.packet_base import packet_base
from pox.lib.packet.packet_utils import *
import pox.lib.packet as pkt
from pox.lib.recoco import Timer
import time
from pox.openflow.of_json import *
import struct

log = core.getLogger()

# s1-s2 measurements
s1s2_start_time = 0.0
s1s2_sent_time1 = 0.0
s1s2_sent_time2 = 0.0
s1s2_received_time1 = 0.0
s1s2_received_time2 = 0.0
s1s2_mytimer = 0
s1s2_OWD1 = 0.0
s1s2_OWD2 = 0.0
s1s2_src_dpid = 0
s1s2_dst_dpid = 0

s1s2_delay = 0

# s1-s3 measurements
s1s3_start_time = 0.0
s1s3_sent_time1 = 0.0
s1s3_sent_time2 = 0.0
s1s3_received_time1 = 0.0
s1s3_received_time2 = 0.0
s1s3_mytimer = 0
s1s3_OWD1 = 0.0
s1s3_OWD2 = 0.0
s1s3_src_dpid = 0
s1s3_dst_dpid = 0

s1s3_delay = 0

# s1-s4 measurements
s1s4_start_time = 0.0
s1s4_sent_time1 = 0.0
s1s4_sent_time2 = 0.0
s1s4_received_time1 = 0.0
s1s4_received_time2 = 0.0
s1s4_mytimer = 0
s1s4_OWD1 = 0.0
s1s4_OWD2 = 0.0
s1s4_src_dpid = 0
s1s4_dst_dpid = 0

s1s4_delay = 0

s1_dpid = 0
s2_dpid = 0
s3_dpid = 0
s4_dpid = 0
s5_dpid = 0

s1_p1 = 0
s1_p4 = 0
s1_p5 = 0
s1_p6 = 0
s2_p1 = 0
s3_p1 = 0
s4_p1 = 0

pre_s1_p1 = 0
pre_s1_p4 = 0
pre_s1_p5 = 0
pre_s1_p6 = 0
pre_s2_p1 = 0
pre_s3_p1 = 0
pre_s4_p1 = 0


# probe protocol packet definition; only timestamp field is present in the header (no payload part)
class myproto(packet_base):
  def __init__(self):
    packet_base.__init__(self)
    self.timestamp=0
  def hdr(self, payload):
    return struct.pack('!I', self.timestamp) # code as unsigned int (I), network byte order (!, big-endian - the most significant byte of a word at the smallest memory address)

class Intent():
  def __init__(self, source_host, destination_host, delay, capacity):
    self.source_host = source_host
    self.destination_host = destination_host
    self.delay = delay
    self.capacity = capacity
    
  def __gt__(self, other):
    if(self.delay > other.delay):
      return True
    else:
      return False
  def __eq__(self, other):
    if(self.delay > other.delay):
      return True
    else:
      return False
  
  def __str__(self):
    msg = "Intend delay %d" % (self.delay)
    return msg

# poprawic od hostow
intent1 = Intent("h3", "10.0.0.6", 300, 100)
intent2 = Intent("h1", "10.0.0.4", 90, 1)
intent3 = Intent("h1", "10.0.0.5", 63, 169)
intent4 = Intent("h3", "10.0.0.6", 80, 10)
intent5 = Intent("h1", "10.0.0.5", 120, 170)
intent6 = Intent("h3", "10.0.0.4", 263, 100)
intent7 = Intent("h2", "10.0.0.5", 16, 121)
intent8 = Intent("h2", "10.0.0.6", 8, 280)
intents = [intent1, intent2, intent3, intent4, intent5, intent6, intent7, intent8 ]


class RoutingController():
  def __init__(self):
    self.intents = []
    self.links_state = self.get_state_of_links() # dict "link_name" : [delay,packet_receives]
    # self.number_of_flows = {"s2": 0, "s3": 0, "s4": 0} # s2, s3, s4
    #self.routing_table = {}

  def sort(self):
    self.intents.sort()
    print "[RoutingController] Intends sorted"

  def get_state_of_links(self):
    self.links_state = {
    "s2": s1s2_delay,
    "s3": s1s3_delay,
    "s4": s1s4_delay
    }
  
  def update(self):
    print "[RoutingController] routing controller updated links info"
    self.get_state_of_links()
    print "\n[RoutingController] Print delay between from s1 to: {}\n".format(routingController.links_state)
    self.routing()
    

  
  def routing(self):
    number_of_flows = {"s2": 0, "s3": 0, "s4": 0}
    loads_of_links = {"s2": 0, "s3": 0, "s4": 0}
    for intent in intents:
      possible_flows = []
      for _, (name_switch, delay) in enumerate(self.links_state.items()):
        if int(intent.delay) > delay:
          possible_flows.append(name_switch)
      result = "[INTENT] src: {}, dst: {}, require_delay: {}, possible_flows: {}".format(intent.source_host, intent.destination_host, intent.delay, possible_flows)
      if len(possible_flows) == 0:
        result = result + " routing without QoS! "
        possible_flows = ["s2", "s3", "s4"]
      flow = self.argmin(possible_flows, number_of_flows, loads_of_links)
      result = result + " send by: {}".format(flow)
      number_of_flows[flow] = number_of_flows[flow] + 1
      loads_of_links[flow] = loads_of_links[flow] + intent.capacity
      self.msg(intent.source_host, intent.destination_host, intent.capacity, flow)    
      print result


    print "[RoutingController] Flow allocation {}".format(number_of_flows)
    print "[RoutingController] Load allocation {}".format(loads_of_links)


  def argmin(self, possible_flows, number_of_flows, loads_of_links):
    min = number_of_flows[possible_flows[0]]
    min_id = possible_flows[0]
    for flow in possible_flows[1:]:
      if number_of_flows[flow] < min: 
          min = number_of_flows[flow]
          min_id = flow
      # checking load balancking
      if number_of_flows[flow] == min:
        if loads_of_links[flow] < loads_of_links[min_id]:
          min = number_of_flows[flow]
          min_id = flow
    return min_id


  def msg(self, source_host, destination_host, capacity, switch):
    flow_table ={'s2': 5, 's3': 6, 's4': 4}
    src_hosts = {'h1': s1_dpid, 'h2': s2_dpid, 'h3': s3_dpid}
    core.openflow.getConnection(src_hosts[source_host]).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    msg = of.ofp_flow_mod()
    msg.command=of.OFPFC_MODIFY_STRICT
    msg.priority =100
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.dl_type = 0x0800
    msg.match.nw_dst = destination_host
    msg.actions.append(of.ofp_action_output(port = int(flow_table[switch])))
    core.openflow.getConnection(src_hosts[source_host]).send(msg)
    

routingController = RoutingController()
routingController.intents = intents
routingController.sort()

def _handle_ConnectionDown (event):
  # Handle connection down - stop the timer for sending the probes
  # TODO: s2-s3-s4 ==> only cancel timer for specific connection
  #global s1s2_mytimer, s1s3_mytimer, s1s4_mytimer
  print "ConnectionDown: ", dpidToStr(event.connection.dpid)

 
def getTheTime():  #function to create a timestamp
  flock = time.localtime()
  then = "[%s-%s-%s" %(str(flock.tm_year),str(flock.tm_mon),str(flock.tm_mday))
 
  if int(flock.tm_hour)<10:
    hrs = "0%s" % (str(flock.tm_hour))
  else:
    hrs = str(flock.tm_hour)
  if int(flock.tm_min)<10:
    mins = "0%s" % (str(flock.tm_min))
  else:
    mins = str(flock.tm_min)
 
  if int(flock.tm_sec)<10:
    secs = "0%s" % (str(flock.tm_sec))
  else:
    secs = str(flock.tm_sec)
 
  then +="]%s.%s.%s" % (hrs,mins,secs)
  return then
 
 
def _timer_func ():
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid
  core.openflow.getConnection(s1_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
  core.openflow.getConnection(s2_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
  core.openflow.getConnection(s3_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
  core.openflow.getConnection(s4_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
  # print getTheTime(), "sent the port stats request to s1_dpid"

  # below, routing in s1 towards h4 (IP=10.0.0.4) is set according to the value of the variable turn
  # turn controls the round robin operation
  # turn=0/1/2 => route through s2/s3/s4, respectively
 

  
  msg = of.ofp_flow_mod()
  msg.command=of.OFPFC_MODIFY_STRICT
  msg.priority =100
  msg.idle_timeout = 0
  msg.hard_timeout = 0
  msg.match.dl_type = 0x0800
  msg.match.nw_dst = "10.0.0.4"
  msg.actions.append(of.ofp_action_output(port = 5))
  core.openflow.getConnection(s1_dpid).send(msg)
  
  # testy routingController
  routingController.update()
  

  # This function is called periodically to send measurement-oriented messages to the switches.
  global s1s2_start_time, s1s2_sent_time1, s1s2_sent_time2, s1s2_src_dpid, s1s2_dst_dpid
 
  # the following executes only when a connection to 'switch0' exists (otherwise AttributeError can be raised)
  if s1s2_src_dpid <>0 and not core.openflow.getConnection(s1s2_src_dpid) is None:

    # send out port_stats_request packet through switch0 connection src_dpid (to measure T1)
    core.openflow.getConnection(s1s2_src_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    s1s2_sent_time1=time.time() * 1000*10 - s1s2_start_time #sending time of stats_req: ctrl => switch0
    # print "sent_time1:", sent_time1

    # sequence of packet formating operations optimised to reduce the delay variation of e-2-e measurements (to measure T3)
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("10:20:00:00:00:00")
    e.dst = EthAddr("20:10:00:00:00:00")
    e.type=0x5577 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type 
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=4)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - s1s2_start_time) #set the timestamp in the probe packet
    # print f.timestamp
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1s2_src_dpid).send(msg)
    #print "=====> probe sent: f=", f.timestamp, " after=", int(time.time()*1000*10 - s1s2_start_time), " [10*ms]"

  # the following executes only when a connection to 'switch1' exists (otherwise AttributeError can be raised)
  if s1s2_dst_dpid <>0 and not core.openflow.getConnection(s1s2_dst_dpid) is None:
    # send out port_stats_request packet through switch1 connection dst_dpid (to measure T2)
    core.openflow.getConnection(s1s2_dst_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    s1s2_sent_time2=time.time() * 1000*10 - s1s2_start_time #sending time of stats_req: ctrl => switch1
    # print "sent_time2:", sent_time2

  # This function is called periodically to send measurement-oriented messages to the switches.
  global s1s3_start_time, s1s3_sent_time1, s1s3_sent_time2, s1s3_src_dpid, s1s3_dst_dpid
 
  # the following executes only when a connection to 'switch0' exists (otherwise AttributeError can be raised)
  if s1s3_src_dpid <>0 and not core.openflow.getConnection(s1s3_src_dpid) is None:

    # send out port_stats_request packet through switch0 connection src_dpid (to measure T1)
    core.openflow.getConnection(s1s3_src_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    s1s3_sent_time1=time.time() * 1000*10 - s1s3_start_time #sending time of stats_req: ctrl => switch0
    # print "sent_time1:", sent_time1

    # sequence of packet formating operations optimised to reduce the delay variation of e-2-e measurements (to measure T3)
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("10:30:00:00:00:00")
    e.dst = EthAddr("30:10:00:00:00:00")
    e.type=0x5578 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type 
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=5)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - s1s3_start_time) #set the timestamp in the probe packet
    # print f.timestamp
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1s3_src_dpid).send(msg)
    #print "=====> probe sent: f=", f.timestamp, " after=", int(time.time()*1000*10 - s1s3_start_time), " [10*ms]"

  # the following executes only when a connection to 'switch1' exists (otherwise AttributeError can be raised)
  if s1s3_dst_dpid <>0 and not core.openflow.getConnection(s1s3_dst_dpid) is None:
    # send out port_stats_request packet through switch1 connection dst_dpid (to measure T2)
    core.openflow.getConnection(s1s3_dst_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    s1s3_sent_time2=time.time() * 1000*10 - s1s3_start_time #sending time of stats_req: ctrl => switch1
    # print "sent_time2:", sent_time2

  # This function is called periodically to send measurement-oriented messages to the switches.
  global s1s4_start_time, s1s4_sent_time1, s1s4_sent_time2, s1s4_src_dpid, s1s4_dst_dpid
 
  # the following executes only when a connection to 'switch0' exists (otherwise AttributeError can be raised)
  if s1s4_src_dpid <>0 and not core.openflow.getConnection(s1s4_src_dpid) is None:

    # send out port_stats_request packet through switch0 connection src_dpid (to measure T1)
    core.openflow.getConnection(s1s4_src_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    s1s4_sent_time1=time.time() * 1000*10 - s1s4_start_time #sending time of stats_req: ctrl => switch0
    # print "sent_time1:", sent_time1

    # sequence of packet formating operations optimised to reduce the delay variation of e-2-e measurements (to measure T3)
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("10:40:00:00:00:00")
    e.dst = EthAddr("40:10:00:00:00:00")
    e.type=0x5579 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type 
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=6)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - s1s4_start_time) #set the timestamp in the probe packet
    # print f.timestamp
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1s4_src_dpid).send(msg)
    #print "=====> probe sent: f=", f.timestamp, " after=", int(time.time()*1000*10 - s1s4_start_time), " [10*ms]"

  # the following executes only when a connection to 'switch1' exists (otherwise AttributeError can be raised)
  if s1s4_dst_dpid <>0 and not core.openflow.getConnection(s1s4_dst_dpid) is None:
    # send out port_stats_request packet through switch1 connection dst_dpid (to measure T2)
    core.openflow.getConnection(s1s4_dst_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    s1s4_sent_time2=time.time() * 1000*10 - s1s4_start_time #sending time of stats_req: ctrl => switch1
    # print "sent_time2:", sent_time2


def _handle_portstats_received (event):
  # Observe the handling of port statistics provided by this function.

  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid
  global s1_p1,s1_p4, s1_p5, s1_p6, s2_p1, s3_p1, s4_p1
  global pre_s1_p1,pre_s1_p4, pre_s1_p5, pre_s1_p6, pre_s2_p1, pre_s3_p1, pre_s4_p1

  if event.connection.dpid==s1_dpid: # The DPID of one of the switches involved in the link
    for f in event.stats:
      if int(f.port_no)<65534:
        if f.port_no==1:
          pre_s1_p1=s1_p1
          s1_p1=f.rx_packets
          # print "s1_p1->","TxDrop:", f.tx_dropped,"RxDrop:",f.rx_dropped,"TxErr:",f.tx_errors,"CRC:",f.rx_crc_err,"Coll:",f.collisions,"Tx:",f.tx_packets,"Rx:",f.rx_packets
        if f.port_no==4:
          pre_s1_p4=s1_p4
          s1_p4=f.tx_packets
          # s1_p4=f.tx_bytes
          # print "s1_p4->","TxDrop:", f.tx_dropped,"RxDrop:",f.rx_dropped,"TxErr:",f.tx_errors,"CRC:",f.rx_crc_err,"Coll:",f.collisions,"Tx:",f.tx_packets,"Rx:",f.rx_packets
        if f.port_no==5:
          pre_s1_p5=s1_p5
          s1_p5=f.tx_packets
        if f.port_no==6:
          pre_s1_p6=s1_p6
          s1_p6=f.tx_packets
 
  if event.connection.dpid==s2_dpid:
     for f in event.stats:
       if int(f.port_no)<65534:
         if f.port_no==1:
           pre_s2_p1=s2_p1
           s2_p1=f.rx_packets
           # s2_p1=f.rx_bytes
     print getTheTime(), "s1_p4(Sent):", (s1_p4-pre_s1_p4), "s2_p1(Received):", (s2_p1-pre_s2_p1)
 
  if event.connection.dpid==s3_dpid:
     for f in event.stats:
       if int(f.port_no)<65534:
         if f.port_no==1:
           pre_s3_p1=s3_p1
           s3_p1=f.rx_packets
     print getTheTime(), "s1_p5(Sent):", (s1_p5-pre_s1_p5), "s3_p1(Received):", (s3_p1-pre_s3_p1)

  if event.connection.dpid==s4_dpid:
     for f in event.stats:
       if int(f.port_no)<65534:
         if f.port_no==1:
           pre_s4_p1=s4_p1
           s4_p1=f.rx_packets
     print getTheTime(), "s1_p6(Sent):", (s1_p6-pre_s1_p6), "s4_p1(Received):", (s4_p1-pre_s4_p1)
  
 

  global s1s2_start_time, s1s2_sent_time1, s1s2_sent_time2, s1s2_received_time1, s1s2_received_time2, s1s2_src_dpid, s1s2_dst_dpid, s1s2_OWD1, s1s2_OWD2

  s1s2_received_time = time.time() * 1000*10 - s1s2_start_time
   # measure T1 as of lab guide
  if event.connection.dpid == s1s2_src_dpid:
    s1s2_OWD1=0.5*(s1s2_received_time - s1s2_sent_time1)
     # print "OWD1: ", OWD1, "ms"s
   # measure T2 as of lab guide
  elif event.connection.dpid == s1s2_dst_dpid:
    s1s2_OWD2=0.5*(s1s2_received_time - s1s2_sent_time2) #originally sent_time1 was here
     # print "OWD2: ", OWD2, "ms"


  global s1s3_start_time, s1s3_sent_time1, s1s3_sent_time2, s1s3_received_time1, s1s3_received_time2, s1s3_src_dpid, s1s3_dst_dpid, s1s3_OWD1, s1s3_OWD2

  s1s3_received_time = time.time() * 1000*10 - s1s3_start_time
   # measure T1 as of lab guide
  if event.connection.dpid == s1s3_src_dpid:
    s1s3_OWD1=0.5*(s1s3_received_time - s1s3_sent_time1)
     # print "OWD1: ", OWD1, "ms"s
   # measure T2 as of lab guide
  elif event.connection.dpid == s1s3_dst_dpid:
    s1s3_OWD2=0.5*(s1s3_received_time - s1s3_sent_time2) #originally sent_time1 was here
     # print "OWD2: ", OWD2, "ms"


  global s1s4_start_time, s1s4_sent_time1, s1s4_sent_time2, s1s4_received_time1, s1s4_received_time2, s1s4_src_dpid, s1s4_dst_dpid, s1s4_OWD1, s1s4_OWD2

  s1s4_received_time = time.time() * 1000*10 - s1s4_start_time
   # measure T1 as of lab guide
  if event.connection.dpid == s1s4_src_dpid:
    s1s4_OWD1=0.5*(s1s4_received_time - s1s4_sent_time1)
     # print "OWD1: ", OWD1, "ms"s
   # measure T2 as of lab guide
  elif event.connection.dpid == s1s4_dst_dpid:
    s1s4_OWD2=0.5*(s1s4_received_time - s1s4_sent_time2) #originally sent_time1 was here
     # print "OWD2: ", OWD2, "ms"


    

def _handle_ConnectionUp (event):
  # waits for connections from all switches, after connecting to all of them it starts a round robin timer for triggering h1-h4 routing changes
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid, s1s2_dst_dpid, s1s2_src_dpid, s1s3_dst_dpid, s1s3_src_dpid, s1s4_dst_dpid, s1s4_src_dpid
  print "ConnectionUp: ",dpidToStr(event.connection.dpid)
 
  # remember the connection dpid for the switch
  for m in event.connection.features.ports:
    if m.name == "s1-eth1":
      # s1_dpid: the DPID (datapath ID) of switch s1;
      s1_dpid = event.connection.dpid
      print "s1_dpid=", s1_dpid
    elif m.name == "s2-eth1":
      s2_dpid = event.connection.dpid
      s1s2_dst_dpid = event.connection.dpid
      print "s2_dpid=", s2_dpid
      print "s1s2_dst_dpid=", s1s2_dst_dpid
    elif m.name == "s3-eth1":
      s3_dpid = event.connection.dpid
      s1s3_dst_dpid = event.connection.dpid
      print "s3_dpid=", s3_dpid
      print "s1s3_dst_dpid=", s1s3_dst_dpid
    elif m.name == "s4-eth1":
      s4_dpid = event.connection.dpid
      s1s4_dst_dpid = event.connection.dpid
      print "s4_dpid=", s4_dpid
      print "s1s4_dst_dpid=", s1s4_dst_dpid
    elif m.name == "s5-eth1":
      s5_dpid = event.connection.dpid
      print "s5_dpid=", s5_dpid
    elif m.name == "s1-eth4":
      s1s2_src_dpid = event.connection.dpid
      print "s1s2_src_dpid=", s1s2_src_dpid
    elif m.name == "s1-eth5":
      s1s3_src_dpid = event.connection.dpid
      print "s1s3_src_dpid=", s1s3_src_dpid
    elif m.name == "s1-eth6":
      s1s4_src_dpid = event.connection.dpid
      print "s1s4_src_dpid=", s1s4_src_dpid
 
  # start 1-second recurring loop timer for round-robin routing changes; _timer_func is to be called on timer expiration to change the flow entry in s1
  if s1_dpid<>0 and s2_dpid<>0 and s3_dpid<>0 and s4_dpid<>0 and s5_dpid<>0:
    Timer(1, _timer_func, recurring=True)

 
def _handle_PacketIn(event):
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid
 
  packet=event.parsed
  # print "_handle_PacketIn is called, packet.type:", packet.type, " event.connection.dpid:", event.connection.dpid


  global s1s2_start_time, s1s2_OWD1, s1s2_OWD2, s1s2_delay

  s1s2_received_time = time.time() * 1000*10 - s1s2_start_time #amount of time elapsed from start_time
 
  if packet.type==0x5577 and event.connection.dpid==s1s2_dst_dpid: #0x5577 is unregistered EtherType, here assigned to probe packets
    # Process a probe packet received in PACKET_IN message from 'switch1' (dst_dpid), previously sent to 'switch0' (src_dpid) in PACKET_OUT.

    c=packet.find('ethernet').payload
    d,=struct.unpack('!I', c)  # note that d,=... is a struct.unpack and always returns a tuple
    #print "[ms*10]: received_time=", int(s1s2_received_time), ", d=", d, ", OWD1=", int(s1s2_OWD1), ", OWD2=", int(s1s2_OWD2)
    s1s2_delay = int(s1s2_received_time - d - s1s2_OWD1 - s1s2_OWD2)/10
    # print "s1-s2 delay:", s1s2_delay, "[ms] <=====" # divide by 10 to normalise to milliseconds


  global s1s3_start_time, s1s3_OWD1, s1s3_OWD2, s1s3_delay

  s1s3_received_time = time.time() * 1000*10 - s1s3_start_time #amount of time elapsed from start_time
 
  if packet.type==0x5578 and event.connection.dpid==s1s3_dst_dpid: #0x5577 is unregistered EtherType, here assigned to probe packets
    # Process a probe packet received in PACKET_IN message from 'switch1' (dst_dpid), previously sent to 'switch0' (src_dpid) in PACKET_OUT.

    c=packet.find('ethernet').payload
    d,=struct.unpack('!I', c)  # note that d,=... is a struct.unpack and always returns a tuple
    #print "[ms*10]: received_time=", int(s1s3_received_time), ", d=", d, ", OWD1=", int(s1s3_OWD1), ", OWD2=", int(s1s3_OWD2)
    s1s3_delay = int(s1s3_received_time - d - s1s3_OWD1 - s1s3_OWD2)/10
    # print "s1-s3 delay:", s1s3_delay, "[ms] <=====" # divide by 10 to normalise to milliseconds
  

  global s1s4_start_time, s1s4_OWD1, s1s4_OWD2, s1s4_delay

  s1s4_received_time = time.time() * 1000*10 - s1s4_start_time #amount of time elapsed from start_time
 
  if packet.type==0x5579 and event.connection.dpid==s1s4_dst_dpid: #0x5577 is unregistered EtherType, here assigned to probe packets
    # Process a probe packet received in PACKET_IN message from 'switch1' (dst_dpid), previously sent to 'switch0' (src_dpid) in PACKET_OUT.

    c=packet.find('ethernet').payload
    d,=struct.unpack('!I', c)  # note that d,=... is a struct.unpack and always returns a tuple
    #print "[ms*10]: received_time=", int(s1s4_received_time), ", d=", d, ", OWD1=", int(s1s4_OWD1), ", OWD2=", int(s1s4_OWD2)
    s1s4_delay = int(s1s4_received_time - d - s1s4_OWD1 - s1s4_OWD2)/10
    # print "s1-s4 delay:", s1s4_delay, "[ms] <=====" # divide by 10 to normalise to milliseconds
  


  # Below, set the default/initial routing rules for all switches and ports.
  # All rules are set up in a given switch on packet_in event received from the switch which means no flow entry has been found in the flow table.
  # This setting up may happen either at the very first pactet being sent or after flow entry expirationn inn the switch
 
  if event.connection.dpid==s1_dpid or event.connection.dpid==s5_dpid:
    a=packet.find('arp')					# If packet object does not encapsulate a packet of the type indicated, find() returns None
    routing_table = { 
       "10.0.0.1": 1,
       "10.0.0.2": 2,
       "10.0.0.3": 3,
       "10.0.0.4": 4,
       "10.0.0.5": 5,
       "10.0.0.6": 6
     }
    if a: 
      msg = of.ofp_packet_out(data=event.ofp)		
    	# Create packet_out message; use the incoming packet as the data for the packet out
      msg.actions.append(of.ofp_action_output(port = routing_table[str(a.protodst)]))		# Add an action to send to the specified port
      event.connection.send(msg)				# Send message to switch

    for _, (ip_add, port) in enumerate(routing_table.items()):
      msg = of.ofp_flow_mod()
      msg.priority =100
      msg.idle_timeout = 0
      msg.hard_timeout = 0
      msg.match.dl_type = 0x0800		# rule for IP packets (x0800)
      msg.match.nw_dst = str(ip_add)
      msg.actions.append(of.ofp_action_output(port = int(port)))
      event.connection.send(msg)
    
  elif event.connection.dpid==s2_dpid or event.connection.dpid==s3_dpid or event.connection.dpid==s4_dpid:
    match_table = [(1, 0x0806, 2), (1, 0x0800, 2), (2, 0x0806, 1), (2, 0x0800, 1)]
    for _, (in_port, dl_type, port) in enumerate(match_table):
      msg = of.ofp_flow_mod()
      msg.priority =10
      msg.idle_timeout = 0
      msg.hard_timeout = 0
      msg.match.in_port = in_port
      msg.match.dl_type= dl_type		# rule for ARP packets (x0806)
      msg.actions.append(of.ofp_action_output(port = port))
      event.connection.send(msg)

# As usually, launch() is the function called by POX to initialize the component (routing_controller.py in our case) 
# indicated by a parameter provided to pox.py 


def launch ():
  global s1s2_start_time, s1s3_start_time, s1s4_start_time
  s1s2_start_time = time.time() * 1000*10
  s1s3_start_time = s1s2_start_time
  s1s4_start_time = s1s2_start_time
  # core is an instance of class POXCore (EventMixin) and it can register objects.
  # An object with name xxx can be registered to core instance which makes this object become a "component" available as pox.core.core.xxx.
  # for examples see e.g. https://noxrepo.github.io/pox-doc/html/#the-openflow-nexus-core-openflow 
  core.openflow.addListenerByName("PortStatsReceived",_handle_portstats_received) # listen for port stats , https://noxrepo.github.io/pox-doc/html/#statistics-events
  core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp) # listen for the establishment of a new control channel with a switch, https://noxrepo.github.io/pox-doc/html/#connectionup
  core.openflow.addListenerByName("PacketIn",_handle_PacketIn) # listen for the reception of packet_in message from switch, https://noxrepo.github.io/pox-doc/html/#packetin
  core.openflow.addListenerByName("ConnectionDown", _handle_ConnectionDown) 
