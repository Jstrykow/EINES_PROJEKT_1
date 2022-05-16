#!/usr/bin/python
 
from lib2to3.pytree import Node
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections
from mininet.log import setLogLevel
from mininet.node import Controller 
from mininet.cli import CLI
from functools import partial
from mininet.node import RemoteController
import time
# Topology: switches interconnected in diamond topology (3 parallel paths, no cross-links); 3 hosts on each side of the diamond

class MyTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self):
        Topo.__init__(self)
        s1=self.addSwitch('s1')
        s2=self.addSwitch('s2')
        s3=self.addSwitch('s3')
        s4=self.addSwitch('s4')
        s5=self.addSwitch('s5')
        h1=self.addHost('h1')
        h2=self.addHost('h2')
        h3=self.addHost('h3')
        h4=self.addHost('h4')
        h5=self.addHost('h5')
        h6=self.addHost('h6')

        self.addLink(h1, s1, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(h2, s1, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(h3, s1, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s1, s2, bw=1, delay='200ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s1, s3, bw=1, delay='50ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s1, s4, bw=1, delay='10ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s2, s5, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s3, s5, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s4, s5, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s5, h4, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s5, h5, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s5, h6, bw=1, delay='0ms', loss=0, max_queue_size=1000, use_htb=True)
        

def perfTest():
    "Create network and run simple performance test"
    topo = MyTopo()
    #net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=POXcontroller1)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=partial(RemoteController, ip='127.0.0.1', port=6633))
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    h1,h2,h3=net.get('h1','h2','h3')
    h4,h5,h6=net.get('h4','h5','h6')
    s1,s2,s3=net.get('s1','s2','s3')
    s4=net.get('s4')
    h1.setMAC("0:0:0:0:0:1")
    h2.setMAC("0:0:0:0:0:2")
    h3.setMAC("0:0:0:0:0:3")
    h4.setMAC("0:0:0:0:0:4")
    h5.setMAC("0:0:0:0:0:5")
    h6.setMAC("0:0:0:0:0:6")
    #s1-s2
    s1.cmd('sudo ip link set dev s1-eth4 down')
    s1.cmd('sudo ip link set dev s1-eth4 address 10:20:00:00:00:00')
    s1.cmd('sudo ip link set dev s1-eth4 up')
        #s2-s1
    s2.cmd('sudo ip link set dev s2-eth1 down')
    s2.cmd('sudo ip link set dev s2-eth1 address 20:10:00:00:00:00')
    s2.cmd('sudo ip link set dev s2-eth1 up')
        #s1-s3
    s1.cmd('sudo ip link set dev s1-eth5 down')
    s1.cmd('sudo ip link set dev s1-eth5 address 10:30:00:00:00:00')
    s1.cmd('sudo ip link set dev s1-eth5 up')
        #s3-s1
    s3.cmd('sudo ip link set dev s3-eth1 down')
    s3.cmd('sudo ip link set dev s3-eth1 address 30:10:00:00:00:00')
    s3.cmd('sudo ip link set dev s3-eth1 up')
        #s1-s4
    s1.cmd('sudo ip link set dev s1-eth6 down')
    s1.cmd('sudo ip link set dev s1-eth6 address 10:40:00:00:00:00')
    s1.cmd('sudo ip link set dev s1-eth6 up')
        #s4-s1
    s4.cmd('sudo ip link set dev s4-eth1 down')
    s4.cmd('sudo ip link set dev s4-eth1 address 40:10:00:00:00:00')
    s4.cmd('sudo ip link set dev s4-eth1 up')

    time.sleep(10)
    s1.cmdPrint('tc qdisc del dev s1-eth4 root')
    s1.cmdPrint('tc qdisc add dev s1-eth4 root handle 10: netem delay 10ms')
    s2.cmdPrint('tc qdisc del dev s2-eth1 root')
    s2.cmdPrint('tc qdisc add dev s2-eth1 root handle 10: netem delay 10ms')

    s1.cmdPrint('tc qdisc del dev s1-eth5 root')
    s1.cmdPrint('tc qdisc add dev s1-eth5 root handle 10: netem delay 200ms')
    s3.cmdPrint('tc qdisc del dev s1-eth1 root')
    s3.cmdPrint('tc qdisc add dev s3-eth1 root handle 10: netem delay 200ms')
    
    s1.cmdPrint('tc qdisc del dev s1-eth6 root')
    s1.cmdPrint('tc qdisc add dev s1-eth6 root handle 10: netem delay 50ms')
    s4.cmdPrint('tc qdisc del dev s4-eth1 root')
    s4.cmdPrint('tc qdisc add dev s4-eth1 root handle 10: netem delay 50ms')

    time.sleep(10)
    s1.cmdPrint('tc qdisc del dev s1-eth4 root')
    s1.cmdPrint('tc qdisc add dev s1-eth4 root handle 10: netem delay 50ms')
    s2.cmdPrint('tc qdisc del dev s2-eth1 root')
    s2.cmdPrint('tc qdisc add dev s2-eth1 root handle 10: netem delay 50ms')

    s1.cmdPrint('tc qdisc del dev s1-eth5 root')
    s1.cmdPrint('tc qdisc add dev s1-eth5 root handle 10: netem delay 10ms')
    s3.cmdPrint('tc qdisc del dev s1-eth1 root')
    s3.cmdPrint('tc qdisc add dev s3-eth1 root handle 10: netem delay 10ms')
    
    s1.cmdPrint('tc qdisc del dev s1-eth6 root')
    s1.cmdPrint('tc qdisc add dev s1-eth6 root handle 10: netem delay 200ms')
    s4.cmdPrint('tc qdisc del dev s4-eth1 root')
    s4.cmdPrint('tc qdisc add dev s4-eth1 root handle 10: netem delay 200ms')

    time.sleep(10)
    s1.cmdPrint('tc qdisc del dev s1-eth4 root')
    s1.cmdPrint('tc qdisc add dev s1-eth4 root handle 10: netem delay 200ms')
    s2.cmdPrint('tc qdisc del dev s2-eth1 root')
    s2.cmdPrint('tc qdisc add dev s2-eth1 root handle 10: netem delay 200ms')

    s1.cmdPrint('tc qdisc del dev s1-eth5 root')
    s1.cmdPrint('tc qdisc add dev s1-eth5 root handle 10: netem delay 50ms')
    s3.cmdPrint('tc qdisc del dev s1-eth1 root')
    s3.cmdPrint('tc qdisc add dev s3-eth1 root handle 10: netem delay 50ms')
    
    s1.cmdPrint('tc qdisc del dev s1-eth6 root')
    s1.cmdPrint('tc qdisc add dev s1-eth6 root handle 10: netem delay 10ms')
    s4.cmdPrint('tc qdisc del dev s4-eth1 root')
    s4.cmdPrint('tc qdisc add dev s4-eth1 root handle 10: netem delay 10ms')

    CLI(net) # launch simple Mininet CLI terminal window
    
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    perfTest()
