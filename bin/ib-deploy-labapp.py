#!/usr/bin/env python
# ****************************************************************************
# Licensed to Qualys, Inc. (QUALYS) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# QUALYS licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ****************************************************************************
import re
import os
import sys
import subprocess
import getpass
from ib.util.parser import *


class InvalidIp( BaseException ) : pass
class InvalidDomain( BaseException ) : pass
class InvalidNs( BaseException ) : pass
class InvalidList( BaseException ) : pass
class InvalidNetwork( BaseException ) : pass

class Domain( object ) :
    _domain_re = re.compile( r'[\w]+\.[\w+]' )
    def __init__( self, name, parent=None ) :
        if parent is None  and  not self._domain_re.match( name ) :
            raise InvalidDomain( str(name) )
        if parent is not None :
            name = name+'.'+parent.Name
        self._name = name
        self._parent = parent
    Name = property( lambda self : self._name )
    Parent = property( lambda self : self._parent )


class Network( object ) :
    _ip_re = re.compile( r'\d{1,3}\.\d{1,3}\.\d{1,3}' )
    def __init__( self, domain, ip, netmask=None, gateway=None, nameservers=None ) :
        if not isinstance(domain, Domain) :
            raise InvalidDomain( str(domain) )
        if type(ip) != str  or  not self._ip_re.match(ip) :
            raise InvalidIp( str(ip) )
        self._domain = domain
        self._ip = ip
        if netmask is None :
            netmask = '255.255.255.0'
        self._netmask = netmask
        if gateway is None :
            gateway = '{}.{}'.format( ip, 1 )
        self._gateway = gateway
        self._nameservers = set()
        if nameservers is not None :
            self.AddNameServers( nameservers )

    def GetHostIp( self, ip ) :
        if type(ip) == int  or  ip.count('.') == 0 :
            return '{}.{}'.format( self._ip, ip )
        elif ip.count('.') == 2 :
            return ip
        else :
            assert False

    def AddNameServers( self, servers ) :
        if not isinstance(servers, (list,tuple,set)) :
            raise InvalidNsList( str(servers) )
        for ns in servers :
            if not isinstance(ns, BaseHost) :
                raise InvalideNs( str(ns) )
            self._nameservers.add( ns )

    def _getNameServerIps( self ) :
        return ','.join( [ns.IpAddr for ns in self._nameservers] )

    Domain        = property( lambda self : self._domain )
    NetIp         = property( lambda self : self._ip )
    NetMask       = property( lambda self : self._netmask )
    Gateway       = property( lambda self : self._gateway )
    NameServers   = property( lambda self : self._nameservers )
    NameServerIps = property( _getNameServerIps )


class BaseHost( object ) :
    _ip_re = re.compile( r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}' )

    def __init__( self, name, domain=None, network=None, ip=None, fqdn=None ) :
        self._checkIp( ip )
        if not( network is None  or  isinstance(network, Network) ) :
            raise InvalidNetwork( str(network) )
        if domain is None  and  network is not None :
            domain = network.Domain
        if domain is None  or  not isinstance(domain, Domain) :
            raise InvalidDomain( str(domain) )
        self._name = name
        self._domain = domain
        self._network = network
        self._ip = ip
        self._fqdn = fqdn

    @classmethod
    def _IpNoneOk( cls ) :
        return True

    @classmethod
    def _checkIp( cls, ip ) :
        if cls._IpNoneOk() is False  and  ip is None :
            raise InvalidIp( str(ip) )
        if not ( (ip is None)  or
                 (type(ip) is int  and  0 < ip < 255)  or
                 (type(ip) is str  and  cls._ip_re.match(ip)) ) :
            raise InvalidIp( str(ip) )

    def _getIp( self ) :
        if type(self._ip) == str :
            return self._ip
        else :
            return '{}.{}'.format(self.Network.NetIp, self._ip)

    def _getFqdn( self ) :
        if self._fqdn is not None :
            return self._fqdn
        else :
            return '{}.{}'.format( self._name, self.Domain.Name )

    Name    = property( lambda self : self._name )
    Domain  = property( lambda self : self._domain )
    Network = property( lambda self : self._network )
    FQDN    = property( _getFqdn )
    IpAddr  = property( _getIp )


class NamedHost( BaseHost ) :
    def __init__( self, name, domain=None, network=None, ip=None, fqdn=None ) :
        BaseHost.__init__( self, name, domain, network, ip, fqdn )

    @classmethod
    def _IpNoneOk( cls ) :
        return True


class Host( BaseHost ) :
    @classmethod
    def _IpNoneOk( cls ) :
        return True


class Sensor( BaseHost ) :
    def __init__( self, name, lab, ip, domain ) :
        BaseHost.__init__( self, name, domain=domain, network=lab.Network, ip=ip )
        self._lab = lab
    Lab = property( lambda self : self._lab )


class DevLab( NamedHost ) :
    def __init__( self, name, clusterid, network, prefix,
                  domain=None, fqdn=None, viphost=None, port=8080, vipurl=None ) :
        NamedHost.__init__( self, name, domain=domain, network=network, fqdn=fqdn )
        self._clusterid = clusterid
        self._prefix = prefix
        if viphost is None :
            viphost = '{}.{}'.format('nsvip01', self.Domain.Name)
        elif viphost.isdigit() :
            viphost = 'nsvip{:02d}.{}'.format(int(viphost), self.Domain.Name)
        elif viphost.count('.') == 0 :
            viphost = '{}.{}'.format(viphost, self.DomainName)
        self._viphost = viphost
        self._port = port
        if vipurl is None :
            vipurl = 'http://{}:{}/'.format(viphost, port)
        self._vipurl = vipurl
        self._sensors = { }

    def _getName( self, num ) :
        return '{}-appliance{:02d}'.format(self._prefix, num)

    def AddSensor( self, num, ip, name=None ) :
        assert ( name is None  and  num is not None ) or ( name is not None  and  num is None )
        if name is None :
            name = self._getName( num )
        self._sensors[num] = Sensor( name, self, ip, self.Domain )

    def GetSensor( self, name=None, num=None ) :
        assert ( name is None  and  num is not None ) or ( name is not None  and  num is None )
        if name is None :
            name = self._getName( num )
        return self._sensors[name]

    ClusterId  = property( lambda self : self._clusterid )
    Network    = property( lambda self : self._network )
    VipUrl     = property( lambda self : self._vipurl )
    ServiceUrl = property( lambda self : self._vipurl )
    UiHost     = property( lambda self : self._name )
    Port       = property( lambda self : self._port )
    Sensors    = property( lambda self : self._sensors.values() )


class VMWareHost( NamedHost ) :
    def __init__( self, name, domain=None, fqdn=None, vmnetwork=None, datastore=None ) :
        NamedHost.__init__( self, name, domain, fqdn )
        if vmnetwork is None :
            vmnetwork = 'Dev Infrastructure'
        self._vmnetwork = vmnetwork
        if datastore is None :
            datastore = '{} datastore1'.format(self.Name)
        self._datastore = datastore

    VmNetwork = property( lambda self : self._vmnetwork )
    Datastore = property( lambda self : self._datastore )

    def Upload( self, user, passwd, sensor, appliance_url, sslpass=None ) :
        if sslpass is None :
            sslpass = 'GARBAGE'
        upload_url = 'vi://{}:{}@vcenter01.{}:443/WAF-MSN/host/{}/'. \
                     format(user, passwd, self.Domain.Name, self.FQDN )
        prop_suffix = 'Qualys_WAF_DailyBuild'
        lab = sensor.Lab
        cmd = (
            '/usr/bin/ovftool',
            '--overwrite',
            '--powerOffTarget',
            '--powerOn',
            '--name={}'.format(sensor.FQDN),
            '--network={}'.format(self.VmNetwork),
            '--datastore={}'.format(self.Datastore),
            '--prop:WAF_CLUSTER_ID={}'.format(lab.ClusterId),
            '--prop:WAF_SERVICE_URL={}'.format(lab.ServiceUrl),
            '--prop:WAF_SSL_PASSPHRASE={}'.format(sslpass),
            '--prop:vami.ip0.{}={}'.format(prop_suffix, sensor.IpAddr),
            '--prop:vami.gateway.{}={}'.format(prop_suffix, lab.Network.Gateway),
            '--prop:vami.netmask0.{}={}'.format(prop_suffix, lab.Network.NetMask),
            '--prop:vami.DNS.{}={}'.format(prop_suffix, lab.Network.NameServerIps),
            appliance_url,
            upload_url,
        )
        return cmd


class Parser( IbBaseParser ) :
    def __init__( self, main, appliances, vmhosts, labs ) :
        IbBaseParser.__init__( self, "Perform {}".format(main.Description) )

        self.Parser.add_argument( '--user', '-u',
                                  action='store', dest='user', default=None,
                                  help='Specify alternate user name' )
        self.Parser.add_argument( '--pass', '-p',
                                  action='store', dest='passwd', default=None,
                                  help='Specify user password' )
        self.Parser.add_argument( '--prefix',
                                  action='store', dest='prefix', default=None,
                                  help='Specify prefix (default = user name)' )

        subparsers = self.Parser.add_subparsers(title='commands',
                                                dest="command",
                                                description='valid commands',
                                                help='command help')

        p = subparsers.add_parser( 'list', help='list arguments' )
        # No options for list

        p = subparsers.add_parser( 'add', help='Add a VMWare host' )
        p.add_argument( 'vmhost', help='VMWare host', nargs='?', choices=vmhosts )
        p.add_argument( 'lab', help='Development lab name', choices=labs )
        p.add_argument( 'appliance_num', type=int, help='Appliance number' )
        p.add_argument( 'which', choices=appliances,
                        help='Specify which appliance' )
        p.add_argument( 'ip', nargs='?', help='IP Address of VM' )
        p.add_argument( '--viphost',
                        action='store', dest='viphost', default=None,
                        help='Override VIP host' )


class Main( object ) :
    def __init__( self ) :
        br = 'http://10.112.129.114/build/'
        self._appliances = {
            'daily' :
            br+'DailyBuildAppliance.1/exports/ova/Qualys-WAF-DailyBuild-Appliance_OVF10.ova',
            'dev' :
            br+'DevAppliance.13/exports/ova/Qualys-WAF-Dev-Appliance_OVF10.ova'
        }
        self._esxinames = ['esxi{:02d}'.format(n) for n in range(1, 10)] + ['waf-vm', 'bitter']
        self._labnames = {
            'dev01' : '9FCB72FB-FF78-498B-8E19-6ADC0180EC29',
            'dev02' : 'DD38B5F8-90A5-4858-9D7F-7C726AA13AD4',
            'dev03' : '38CC7D16-0980-47B7-A19F-1B210F242B5A',
            'qa'    : 'F9804CB8-BBA5-4089-B0AB-2E4B054746B4',
        }

        self._parser = Parser( self,
                               self._appliances.keys(),
                               self._esxinames,
                               self._labnames.keys() )

    def _Setup( self ) :
        msn = Domain( 'msn01.qualys.com' )
        net128 = Network( msn, '10.112.128' )
        net129 = Network( msn, '10.112.129' )
        nservers = (
            NamedHost( 'ns1', network=net128, ip=121 ),
            NamedHost( 'ns2', network=net128, ip=122 ),
        )
        net128.AddNameServers( nservers )
        net129.AddNameServers( nservers )

        self._esxihosts = dict( [(name,VMWareHost(name, msn)) for name in self._esxinames] )

        self._labs = dict( )
        for name,clusterid in self._labnames.items() :
            domain = Domain( name, parent=msn )
            self._labs[name] = DevLab( name, clusterid, net129,
                                       prefix=self._args.prefix,
                                       domain=domain,
                                       viphost=self._args.viphost )

        self._labs['dev01'].AddSensor( 1, 113 )
        self._labs['dev03'].AddSensor( 1, 118 )
        self._labs['dev03'].AddSensor( 2, 119 )
        self._labs['dev03'].AddSensor( 3, 120 )
        self._labs['dev03'].AddSensor( 4, 125 )
        self._labs['qa'].AddSensor( 1, 161 )
        self._labs['qa'].AddSensor( 1, 162 )


    def _Parse( self ) :
        self._args = self._parser.Parse()
        if self._args.user is None :
            self._args.user = getpass.getuser( )
        if self._args.prefix is None :
            self._args.prefix = self._args.user

    Description = property( lambda self : 'Deploy appliance' )

    def Main( self ) :
        self._Parse( )
        self._Setup( )
        if self._args.command == 'list' :
            print 'ESXI Hosts:', ' '.join( [host.Name for host in self._esxihosts.values()] )
            print 'Appliances:', ' '.join( self._appliances.keys() )
            print 'Labs:', ' '.join( self._labs.keys() )
            for key,lab in self._labs.items() :
                print '  {} sensors: {}'.format( key, ' '.join([s.Name for s in lab.Sensors]) )
            sys.exit( 0 )
        if self._args.passwd is None :
            self._args.passwd = getpass.getpass( 'Password for user {}: '.format(self._args.user) )

        lab = self._labs[self._args.lab]
        vmhost = self._esxihosts[self._args.vmhost]
        sensor = lab.GetSensor( self._args.appliance_num )
        cmd = vmhost.Upload( self._args.user,
                             self._args.passwd,
                             sensor,
                             self._appliances[self._args.which] )
        if self._args.verbose >= 2 and not self._args.execute :
            print 'Not executing command:'
            print ' \\\n  '.join(cmd)
        elif self._args.verbose :
            print 'Executing:', cmd
        if self._args.execute :
            subprocess.call( cmd )

main = Main( )
main.Main( )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
