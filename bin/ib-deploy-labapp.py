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
import argparse
import subprocess
import getpass
import uuid
import time

from ib.util.parser import *
from ib.util.version import *


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

    def __init__( self, name, domain, network=None, ip=None, fqdn=None ) :
        self._checkIp( ip )
        if not( network is None  or  isinstance(network, Network) ) :
            raise InvalidNetwork( str(network) )
        if domain is not None  and  not isinstance(domain, Domain) :
            raise InvalidDomain( str(domain) )
        self._name = name
        self._domain = domain
        self._network = network
        self._ip = ip
        self._fqdn = fqdn

    @classmethod
    def _IpNoneOk( cls ) :
        return False

    @classmethod
    def _checkIp( cls, ip ) :
        if ip is None :
            if not cls._IpNoneOk() :
                raise InvalidIp( str(ip) )
            return
        if not ( (type(ip) is int  and  0 < ip < 255)  or
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
    def __init__( self, name, domain, network=None, ip=None, fqdn=None ) :
        BaseHost.__init__( self, name, domain, network, ip, fqdn )


class Host( BaseHost ) :
    def __init__( self, name, domain, network=None, ip=None, fqdn=None ) :
        BaseHost.__init__( self, name, domain, network, ip, fqdn )

    @classmethod
    def _IpNoneOk( cls ) :
        return True


class Sensor( BaseHost ) :
    def __init__( self, name, lab, ip, domain ) :
        BaseHost.__init__( self, name, domain=domain, network=lab.Network, ip=ip )
        self._lab = lab
    Lab = property( lambda self : self._lab )


class BaseLabInfo( object ) :
    def __init__( self, name, domain, hosts=None ) :
        assert type(name) == str
        self._name = name
        self._domain = domain
        self._hosts = {} if hosts is None else hosts

    def CreateLab( self, main, network ) :
        return BaseLab( main, self, network, domain=self._domain )

    @classmethod
    def _IpNoneOk( cls ) :
        return True

    def _getHosts( self ) :
        for num,ip in self._hosts.items() :
            yield num,ip

    Name     = property( lambda self : self._name )
    NumHosts = property( lambda self : len(self._hosts) )
    Hosts    = property( _getHosts )


class DevLabInfo( BaseLabInfo ) :
    def __init__( self, name, domain, clusterid=None, sensors=None, viphost=None ) :
        subdomain = Domain( name, parent=domain )
        BaseLabInfo.__init__( self, name, subdomain, hosts=sensors )
        if clusterid is None :
            self._clusterid = None
        else : 
            self._clusterid = uuid.UUID( clusterid )
        assert viphost is None or type(viphost) in (int,str)
        self._viphost = viphost

    def GetHostName( self, prefix, num ) :
        return '{}-appliance{:02d}'.format(prefix, num)

    def CreateLab( self, main, network ) :
        return DevLab( main, self, network, domain=self._domain )

    ClusterId    = property( lambda self : self._clusterid )
    ClusterIdStr = property( lambda self : str(self._clusterid) )
    VipHost      = property( lambda self : self._viphost )
    NumSensors   = property( lambda self : self.NumHosts)
    Sensors      = property( BaseLabInfo._getHosts )


class TargetLabInfo( BaseLabInfo ) :
    def GetHostName( self, prefix, num ) :
        return '{}-target{:02d}'.format(prefix, num)


class ZapLabInfo( BaseLabInfo ) :
    def GetHostName( self, prefix, num ) :
        return '{}-zap{:02d}'.format(prefix, num)


class BaseLab( NamedHost ) :
    def __init__( self, main, labinfo, network, domain=None, fqdn=None ) :
        NamedHost.__init__( self, labinfo.Name, domain=domain, network=network, fqdn=fqdn )
        self._main = main
        self._labinfo = labinfo
        self._hosts = { }

    @classmethod
    def _IpNoneOk( cls ) :
        return True

    LabInfo = property( lambda self : self._labinfo )
    Network = property( lambda self : self._network )
    Hosts   = property( lambda self : self._hosts.values() )

    def AddHostsFromLabInfo( self ) :
        self.AddHosts( self.LabInfo.Hosts )

    def AddHosts( self, hosts ) :
        for num,ip in hosts :
            self.AddHost( num, ip )

    def AddHost( self, num, ip, name=None ) :
        assert ( name is None  and  num is not None ) or ( name is not None  and  num is None )
        if name is None :
            name = self.LabInfo.GetHostName( self._main.Prefix, num )
        self._hosts[name] = self._CreateHost( name, ip )

    def GetHost( self, name=None, num=None ) :
        assert ( name is None  and  num is not None ) or ( name is not None  and  num is None )
        if name is None :
            name = self.LabInfo.GetHostName( self._main.Prefix, num )
        try :
            return self._hosts[name]
        except KeyError :
            return None

    def _CreateHost( self, name, ip ) :
        return Host( name, self.Domain, self.Network, ip )


class DevLab( BaseLab ) :
    def __init__( self, main, labinfo, network,
                  domain=None, fqdn=None, viphost=None, port=8080, vipurl=None ) :
        BaseLab.__init__( self, main, labinfo, network, domain=domain, fqdn=fqdn )
        self.SetVip( viphost, port, vipurl )

    def SetVip( self, viphost=None, port=8080, vipurl=None ) :
        if viphost is None :
            viphost = self.LabInfo.VipHost
        if viphost is None :
            nsvip = '{}.{}'.format('nsvip01', self.Domain.Name)
        elif type(viphost) == int  or  viphost.isdigit() :
            nsvip = 'nsvip{:02d}.{}'.format(int(viphost), self.Domain.Name)
        elif viphost.count('.') == 0 :
            nsvip = '{}.{}'.format(viphost, self.DomainName)
        else :
            nsvip = viphost
        self._viphost = nsvip
        self._port = port
        if vipurl is None :
            vipurl = 'http://{}:{}/'.format(nsvip, port)
        self._vipurl = vipurl

    def _CreateHost( self, name, ip ) :
        return Sensor( name, self, ip, self.Domain )

    ClusterId    = property( lambda self : self._labinfo.ClusterId )
    ClusterIdStr = property( lambda self : self._labinfo.ClusterIdStr )
    VipUrl       = property( lambda self : self._vipurl )
    ServiceUrl   = property( lambda self : self._vipurl )
    UiHost       = property( lambda self : self._name )
    Port         = property( lambda self : self._port )
    Sensors      = property( lambda self : self.Hosts )


class Appliance( object ) :
    def __init__( self, name, rev, ova=None, local_file=None, url=None, prop_suffix=None ) :
        assert isinstance(rev, IbVersion)
        assert IbVersion('0.9') <= rev <= IbVersion('1.2')

        self._name = name
        self._rev = rev
        self.Setup( ova, local_file, url )
        self.PropSuffix = prop_suffix

    def Setup( self, ova=None, local_file=None, url=None ) :
        if ova is None :
            if self.Rev >= IbVersion('1.1') :
                ova = 'Qualys-WAF-{}-Appliance_OVF10.ova'.format( self.Name )
            else :
                ova = 'QualysGuard-WAF_OVF10.ova'
        self._ova = ova
        if url is None :
            if local_file is not None :
                url = 'file://'+local_file
            else :
                url = 'http://10.112.129.114/build/{}Appliance.1/exports/ova/{}'.format(self.Name, ova)
        self._url = url

    def _SetPropSuffix( self, prop_suffix ) :
        if prop_suffix is None :
            if self.Rev >= IbVersion('1.2') :
                prop_suffix = 'Qualys_WAF_{}'.format( self.Name )
            else :
                prop_suffix = 'Qualys_WAF'
        self._prop_suffix = prop_suffix

    Name       = property( lambda self : self._name )
    Rev        = property( lambda self : self._rev )
    Ova        = property( lambda self : self._ova )
    Url        = property( lambda self : self._url )
    PropSuffix = property( lambda self : self._prop_suffix, _SetPropSuffix )


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

    @classmethod
    def _IpNoneOk( cls ) :
        return True

    def UploadCommand( self, user, passwd, host, lab, appliance, sslpass=None, force=False ) :
        assert isinstance(appliance, Appliance)
        if sslpass is None :
            sslpass = 'GARBAGE'
        upload_url = 'vi://{}:{}@vcenter01.{}:443/WAF-MSN/host/{}/'. \
                     format(user, passwd, self.Domain.Name, self.FQDN )
        if appliance.Rev >= IbVersion('1.1') :
            prop_ID = 'WAF_CLUSTER_ID'
            prop_URL = 'WAF_SERVICE_URL'
        else :
            prop_ID = 'RNS_TOKEN'
            prop_URL = 'RNS_URL'
        cmd = [ '/usr/bin/ovftool' ]
        if force :
            cmd += [ '--overwrite', '--powerOffTarget', ]
        cmd += [
            '--powerOn',
            '--name={}'.format(host.FQDN),
            '--network={}'.format(self.VmNetwork),
            '--datastore={}'.format(self.Datastore),
            ]
        if isinstance(lab, DevLab) :
            cmd += [
                '--prop:{}={}'.format(prop_ID, lab.ClusterIdStr),
                '--prop:{}={}'.format(prop_URL, lab.ServiceUrl),
                '--prop:WAF_SSL_PASSPHRASE={}'.format(sslpass),
                '--prop:vami.ip0.{}={}'.format(appliance.PropSuffix, host.IpAddr),
                '--prop:vami.gateway.{}={}'.format(appliance.PropSuffix, lab.Network.Gateway),
                '--prop:vami.netmask0.{}={}'.format(appliance.PropSuffix, lab.Network.NetMask),
                '--prop:vami.DNS.{}={}'.format(appliance.PropSuffix, lab.Network.NameServerIps),
                ]
        cmd += [
            appliance.Url,
            upload_url,
        ]
        return cmd


class Parser( IbBaseParser ) :
    def __init__( self, main ) :
        IbBaseParser.__init__( self, "Perform {}".format(main.Description),
                               formatter_class=argparse.RawDescriptionHelpFormatter,
                               epilog=\
'''
Examples:
   ib-deploy-labapp.py list
   ib-deploy-labapp.py -v deploy esxi06 dev03 1 next
   ib-deploy-labapp.py deploy esxi06 dev03 1 file:Qualys-WAF-Dev-Appliance_OVF10.ova -f
   ib-deploy-labapp.py deploy vmwaf-vm NONE 0 file:openSUSE_13.1_qualysZAP64.x86_64-0.2.4.ovf
'''
        )

        class ApplianceAction(argparse.Action):
            @classmethod
            def Setup( cls, names, patterns ) :
                cls._patterns = tuple(patterns)
                cls._names    = ','.join(names)
            def __call__(self, parser, namespace, values, option_string=None):
                for pat in self._patterns :
                    m = pat.match(values)
                    if m is not None :
                        namespace.appliance_name = m.group(1)
                        break
                else :
                    parser.error( 'Invalid appliance name "{}"\n\tValid names: {}'
                                  .format(values,self._names) )
        self._appliance_names  = tuple([a for a in (list(main.ApplNames)+['file:<name>'])])
        patterns  = [re.compile('('+a+')$') for a in main.ApplNames]
        patterns += [re.compile(r'file:(.*)')]
        ApplianceAction.Setup( self._appliance_names, patterns )

        self.Parser.add_argument( '--user', '-u',
                                  action='store', dest='user', default=None,
                                  help='Specify alternate user name' )
        self.Parser.add_argument( '--pass', '-p',
                                  action='store', dest='passwd', default=None,
                                  help='Specify user password' )
        self.Parser.add_argument( '--prefix',
                                  action='store', dest='prefix', default=None,
                                  help='Specify prefix (default = user name)' )
        self.Parser.add_argument( '--rev',
                                  action='store', dest='appliance_rev', default=None,
                                  help='Specify appliance revision (default = <appliance specific>)' )
        self.Parser.add_argument( '--appliance-url',
                                  action='store', dest='appliance_url', default=None,
                                  help='Specify appliance url (default = <appliance specific>)' )
        self.Parser.add_argument( '--vsphere-rev',
                                  action='store', dest='vsphere_rev', default='5.1',
                                  help='Specify vSphere version (default = 5.1' )

        self.Parser.set_defaults( viphost=None, force=False )

        subparsers = self.Parser.add_subparsers(title='commands',
                                                dest="command",
                                                description='valid commands',
                                                help='command help')

        p = subparsers.add_parser( 'list', help='list arguments' )
        # No options for list

        p = subparsers.add_parser( 'deploy', help='Deploy a sensor to VCenter' )
        p.add_argument( 'vmhost', help='VMWare host', choices=main.EsxiNames )
        p.add_argument( 'lab', help='Development lab name', choices=main.LabNames )
        p.add_argument( 'appliance_num', type=int, help='Appliance number' )
        p.add_argument( 'which', action=ApplianceAction,
                        help='Specify which appliance ({})'.format(','.join(self._appliance_names)) )
        p.add_argument( 'ip', nargs='?', help='IP Address of VM' )
        p.add_argument( 'hostname', nargs='?', help='Host Name of VM' )

        p.add_argument( '--viphost', action='store', dest='viphost', help='Override VIP host' )
        p.add_argument( '--force', '-f',
                        action='store_true', dest='force', help='Force (default = False)' )
        p.add_argument( '--no-force', action='store_false', dest='force', help='Disable force' )
        p.add_argument( '--ova-name',
                        action='store', dest='ova_name', default=None,
                        help='Override name of remote OVA' )


class Main( object ) :
    def __init__( self ) :
        self._InitAppliances( )
        self._InitNet( )
        self._InitLabs( )
        self._InitEsxiHosts( )
        self._parser = Parser( self )

    def _InitAppliances( self ) :
        self._appliances = {
            'daily' : Appliance( 'DailyBuild', rev=IbVersion('1.2') ),
            'next'  : Appliance( 'NextRelease', rev=IbVersion('1.2') ),
            'dev'   : Appliance( 'Dev', rev=IbVersion('1.1') ),
            'prod'  : Appliance( 'Prod', rev=IbVersion('1.1') ),
        }

    def _InitNet( self ) :
        self._msn = Domain( 'msn01.qualys.com' )
        self._nets = {
            128 : Network( self._msn, '10.112.128' ),
            129 : Network( self._msn, '10.112.129' ),
        }
        nservers = (
            NamedHost( 'ns1', domain=self._msn, network=self._nets[128], ip=121 ),
            NamedHost( 'ns2', domain=self._msn, network=self._nets[128], ip=122 ),
        )
        self._nets[128].AddNameServers( nservers )
        self._nets[129].AddNameServers( nservers )

    def _InitLabs( self ) :
        labinfo = (
            DevLabInfo(
                'dev01',
                self._msn,
                '9FCB72FB-FF78-498B-8E19-6ADC0180EC29',
                sensors={ 1:113 },
            ),
            DevLabInfo(
                'dev02',
                self._msn,
                'DD38B5F8-90A5-4858-9D7F-7C726AA13AD4',
                sensors={ 1:116, 2:165 },
            ),
            DevLabInfo(
                'dev03',
                self._msn,
                '38CC7D16-0980-47B7-A19F-1B210F242B5A',
                sensors={ 1:118, 2:119, 3:120, 4:121 },
                viphost=2,
            ),
            DevLabInfo(
                'qa',
                self._msn,
                'F9804CB8-BBA5-4089-B0AB-2E4B054746B4',
                sensors={ 1:161, 2:162 },
            ),
            ZapLabInfo(
                'ZAP',
                self._msn,
                hosts={ 1:135, 2:136, 3:160, 4:166 },
            ),
            TargetLabInfo(
                'Targets',
                self._msn,
                hosts={ 1:135, 2:136, 3:160, 4:166 },
            ),
        )
        self._labs = dict( )
        for labinfo in labinfo :
            self._labs[labinfo.Name] = labinfo.CreateLab( self, self._nets[129] )

    def _InitEsxiHosts( self ) :
        names = ['esxi{:02d}'.format(n) for n in range(1, 10)] + ['bitter']
        self._esxi_hosts = dict( [(name,VMWareHost(name, self._msn)) for name in names] )
        self._esxi_hosts['waf-vm'] = VMWareHost('waf-vm', self._msn, datastore='datastore1 (1)')

    EsxiNames   = property( lambda self : self._esxi_hosts.keys() )
    ApplNames   = property( lambda self : self._appliances.keys() )
    Prefix      = property( lambda self : self._args.prefix )
    LabNames    = property( lambda self : self._labs.keys() )
    Description = property( lambda self : 'Deploy appliance' )

    def _Parse( self ) :
        self._args = self._parser.Parse()
        if self._args.user is None :
            self._args.user = getpass.getuser( )
        if self._args.prefix is None :
            self._args.prefix = self._args.user
        if self._args.command != "list"  and \
           self._args.appliance_name not in self.ApplNames and \
           not os.path.isfile(self._args.appliance_name) :
            self._parser.Error( 'Appliance file "{}" does not exist'.format(self._args.appliance_name) )

    def _PostParse( self ) :
        if self._args.command != "list"  and  self._args.execute  and  self._args.passwd is None :
            self._args.passwd = getpass.getpass( 'Enter password for user {}: '.format(self._args.user) )

        # Finish setting up lab things with command line values
        for lab in self._labs.values() :
            lab.Prefix = self._args.prefix
            lab.AddHostsFromLabInfo( )
            if isinstance( lab, DevLab ) :
                lab.SetVip( viphost=self._args.viphost )

    def Main( self ) :
        self._Parse( )
        self._PostParse( )
        if self._args.command == 'list' :
            print 'List of known items:'
            names = sorted([host.Name for host in self._esxi_hosts.values()])
            print '  ESXI Hosts:', ' '.join(names)
            names = sorted(self._appliances.keys())
            print '  Appliances:', ' '.join(names)
            names = sorted(self._labs.keys())
            print '  Labs:', ' '.join(names)
            for key,lab in sorted(self._labs.items(), key=lambda t: t[0].lower()) :
                if len(lab.Hosts) :
                    print '    {} hosts: {}'. \
                        format( key, ' '.join(sorted([s.Name for s in lab.Hosts])) )
            sys.exit( 0 )

        lab = self._labs[self._args.lab]
        vmhost = self._esxi_hosts[self._args.vmhost]
        host = lab.GetHost( num=self._args.appliance_num )
        appliance = self._appliances.get(
            self._args.appliance_name,
            Appliance('File', rev=IbVersion('1.0'), local_file=self._args.appliance_name)
        )
        cmd = vmhost.UploadCommand( self._args.user,
                                    self._args.passwd,
                                    host,
                                    lab,
                                    appliance,
                                    force=self._args.force )

        clean = vmhost.UploadCommand( self._args.user,
                                      'XXXXXX',
                                      host,
                                      lab,
                                      appliance,
                                      force=self._args.force )
        if not self._args.execute :
            if self._args.verbose >= 2 :
                print 'Not executing:', '\\\n"'+'"\\\n  "'.join(clean)+'"'
            else :
                print 'Not executing:', clean
        elif self._args.verbose >= 2 :
            print 'Executing:', '\\\n"'+'"\\\n  "'.join(clean)+'"'
        elif self._args.verbose :
            print 'Executing:', clean
        if self._args.execute :
            subprocess.call( cmd )
        if not self._args.quiet :
            print 'Finished deploying to {} ({}) @ {}' \
                .format(host.Name, host.IpAddr, time.asctime())

main = Main( )
main.Main( )

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
