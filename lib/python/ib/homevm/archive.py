#! /usr/bin/env python
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
import time

from ib.util.version      import *
from ib.homevm.exceptions import *

# Home VM Archive
class IbHomeVmArchive( object ) :
    class _DataItem( object ) :
        def __init__( self, name, required, _type, validator=None, getfn=None ) :
            assert validator is None  or  callable(validator)
            self._name = name
            self._required = required
            self._type = _type
            self._validator = validator
            self._getfn = getfn
        Name      = property( lambda self : self._name )
        Required  = property( lambda self : self._required )
        Validator = property( lambda self : self._validator )
        GetFn     = property( lambda self : self._getfn )

    class _ArchiveRec( object ) :
        def __init__( self, name, filename, destdir ) :
            self._name = name
            self._filename = filename
            self._destdir = destdir
        Name     = property( lambda self : self._name )
        FileName = property( lambda self : self._filename )
        DestDir  = property( lambda self : self._destdir )
        def __str__( self ) :
            return '"{r.Name}": "{r.FileName}" -> "{r.DestDir}"'.format(r=self)

    _version_re     = re.compile(r'\d+\.\d+(?:\.\d+)?$')
    _commit_re      = re.compile(r'[0-9a-fA-F]{8,40}$')
    _config_re      = re.compile(r'(\S*/)?configure(\s.*)?$')
    _ats_version_re = re.compile(r'\d+(\.(\d+|x)){1,3}(?:-\w+)?$')

    _item_names = dict( [ (p.Name, p) for p in (
        _DataItem( 'ArchiveDirectory',      True,  str ),
        _DataItem( 'Name',                  True,  str ),
        _DataItem( 'TimeStamp',             True,  float ),
        _DataItem( 'QualysLocal',           True,  str ),
        _DataItem( 'IronBeeVersion',        True,  IbVersion ),
        _DataItem( 'IronBeeGitBranch',      True,  str ),
        _DataItem( 'IronBeeGitCommit',      False, str,
                   lambda cls,value : cls._commit_re.match(value) ),
        _DataItem( 'Architecture',          True,  str ),
        _DataItem( 'Bits',                  True,  int ),
        _DataItem( 'EtcInGitBranch',        True,  str ),
        _DataItem( 'EtcInGitCommit',        False, str,
                   lambda cls,value : cls._commit_re.match(value) ),
        _DataItem( 'EtcInRepo',             False, str ),
        _DataItem( 'BuildConfig',           False, str,
                   lambda cls,value : value is None or cls._config_re.match(value) ),
        _DataItem( 'Compiler',              True,  str ),
        _DataItem( 'GccVersion',            True,  str,
                   lambda cls,value : cls._version_re.match(value) ),
        _DataItem( 'ClangVersion',          False, str,
                   lambda cls,value : cls._version_re.match(value) ),
        _DataItem( 'ClangThreadSanitizer',  False, bool ),
        _DataItem( 'AtsVersion',            False, str,
                   lambda cls,value : cls._ats_version_re.match(value) ),
    ) ] )

    def __init__( self ) :
        self._items = dict( )
        self._archives = [ ]

    @classmethod
    def _CheckValue( cls, name, value, item=None ) :
        try :
            if item is None :
                item = cls._item_names[name]
            if item.Validator is not None :
                return item.Validator(cls, value)
            else :
                return True
        except KeyError :
            raise IbHomeVmDataError( 'Attempt to set check attribute "{0}"'.format(name) )

    def __setattr__( self, name, value ) :
        if name.startswith('_'):
            super(IbHomeVmArchive, self).__setattr__(name, value)
            return
        elif name not in self._item_names :
            raise IbHomeVmDataError( 'Attempt to set invalid attribute "{0}"'.format(name) )
        try :
            item = self._item_names[name]
            converted = item._type( value )
            if not self._CheckValue( name, converted, item ) :
                raise ValueError
            self._items[name] = converted
        except ( ValueError, IbHomeVmDataError ) :
            raise IbHomeVmValueError( 'Attempt to set "{0}" to invalid value "{1}"'.
                                         format(name, str(value)) )

    def __getattr__( self, name ) :
        if name not in self._item_names :
            raise IbHomeVmDataError( 'Attempt to access invalid attribute "{0}"'.format(name) )
        return self._items.get(name, None)

    def Get( self, name, default=None ) :
        if name not in self._item_names :
            raise IbHomeVmDataError( 'Attempt to access invalid attribute "{0}"'.format(name) )
        return self._items.get(name, default)

    # Vm time stamp format for strftime()
    _TimeStampFormat = '%Y.%m.%d.%H.%M.%S'
    @classmethod
    def FormatTime( cls, when ) :
        s1 = time.strftime( cls._TimeStampFormat, time.localtime(when) )
        s2 = '{:.02f}'.format(when).split('.')[1]
        return s1+'.'+s2

    TimeString = property( lambda self : self.FormatTime(self.TimeStamp) )

    def _GetBase( self ) :
        if self.Name is not None :
            return self.Name
        try :
            ts = self.TimeString
            self.Name = ts
            return ts
        except KeyError as e :
            raise IbHomeVmException( "Missing items:"+str(e) )
            
    def GetPath( self, archive_root, filename=None ) :
        base = self._GetBase( )
        if self.ArchiveDirectory is None :
            self.ArchiveDirectory = os.path.join( archive_root, base )
        if filename is None :
            return self.ArchiveDirectory
        else :
            return os.path.join( self.ArchiveDirectory, filename )

    def AddArchive( self, name, filename, destdir ) :
        rec = self._ArchiveRec( name, filename, destdir )
        self._archives.append( rec )

    def GetArchive( self, name ) :
        for rec in self._archives :
            if rec.Name == name :
                return rec
        else :
            raise( 'No archive named: "{0}"'.format(name) )

    def Validate( self ) :
        for name,item in self._item_names.items() :
            value = self.Get(name)
            if item.Required and value is None :
                raise IbHomeVmException( "Missing item: "+name )
            elif value is not None  and  item.Validator is not None :
                item.Validator(self, value)

    def WriteArchiveData( self, archive_dir ) :
        path = self.GetPath( archive_dir, 'archives.txt' )
        self.Validate( )
        with open(path, 'w') as fp :
            for name,value in self._items.items( ) :
                if value is not None :
                    print >>fp, name+'='+str(value)
            for rec in self._archives :
                print >>fp, "Archive:{r.Name}={r.FileName},{r.DestDir}".format(r=rec)

    _archive_rec_re = re.compile( r'Archive:([\w\-]+)$' )
    def ReadArchiveData( self, archive_dir ) :
        path = os.path.join( archive_dir, 'archives.txt' )
        try :
            fp = open(path)
            for lno,line in enumerate(fp) :
                try :
                    name,value = line.strip().split('=', 1)
                except ValueError as e :
                    print 'Failed to parse line {:d} of "{:s}"'.format(lno+1, path)
                m = self._archive_rec_re.match( name )
                if m is not None  and  ',' in value :
                    (filename, destdir) = value.split(',', 1)
                    rec = self._ArchiveRec( m.group(1), filename, destdir )
                    self._archives.append( rec )
                else :
                    self.__setattr__(name, value)
        except IOError as e :
            raise IbHomeVmException( 'Failed to read archive file "{0}": {1}'.format(path, e) )

    @classmethod
    def CreateFromFile( cls, archive_path ) :
        try :
            vm = cls( )
            vm.ReadArchiveData( archive_path )
            vm.Validate( )
            return vm
        except IbHomeVmException as e :
            print e
            return None

    def __str__( self ) :
        return str(self._items)


class IbHomeVmArchiveSet( object ) :
    def __init__( self, archives_dir ) :
        self._archives_dir = archives_dir
        self._archives = [ ]
    ArchivesDir = property( lambda self : self._archives_dir )

    def ReadAll( self ) :
        for name in os.listdir( self._archives_dir ) :
            full = os.path.join(self._archives_dir, name)
            if not os.path.isdir( full ) :
                continue
            vm = IbHomeVmArchive.CreateFromFile( full )
            if vm is not None :
                self._archives.append( vm )

    def Archives( self, filter=None ) :
        for archive in self._archives :
            if filter is None or filter(archive) :
                yield archive
        return


if __name__ == "__main__" :
    data = IbHomeVmArchive( )
    try :
        data.foo = 'abc'
        assert False
    except IbHomeVmDataError as e :
        pass

    try :
        now = time.time()
        s = IbHomeVmBuild.FormatTime( now )
        data.TimeStamp = now
        time.sleep(0.2)
        assert data.TimeStamp == now
        assert data.TimeString == s
    except IbHomeVmDataError as e :
        raise

    try :
        data.IronBeeVersion = IbVersion('0.11.3')
        assert type(data.IronBeeVersion) == IbVersion
        assert str(data.IronBeeVersion) == '0.11.3'
    except IbHomeVmError as e :
        raise

    try :
        data.IronBeeVersion = '0.11.3'
    except IbHomeVmException as e :
        pass

    try :
        data.IronBeeGitBranch = "master"
        assert data.IronBeeGitBranch == "master"
    except IbHomeVmException as e :
        raise

    try :
        data.IronBeeGitCommit = "7a98ec3b"
        assert data.IronBeeGitCommit == "7a98ec3b"
    except IbHomeVmException as e :
        raise

    try :
        data.IronBeeGitCommit = "7a98ec3bx"
        assert False
    except IbHomeVmValueError as e :
        pass

    try :
        data.EtcInGitCommit = "520c3a59bd5937e98d650c440337345317744cc0"
        assert data.EtcInGitCommit == "520c3a59bd5937e98d650c440337345317744cc0"
    except IbHomeVmException as e :
        raise

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/configure"
        assert data.BuildConfig == "/home/nick/devel/qualys/ib/configure"
    except IbHomeVmException as e :
        raise

    try :
        data.BuildConfig = "./configure"
        assert data.BuildConfig == "./configure"
    except IbHomeVmException as e :
        raise

    try :
        data.BuildConfig = "./xconfigure"
        assert False
    except IbHomeVmValueError as e :
        pass

    try :
        data.BuildConfig = "configure"
        assert data.BuildConfig == "configure"
    except IbHomeVmException as e :
        raise

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/configure --foo=bar"
        assert data.BuildConfig == "/home/nick/devel/qualys/ib/configure --foo=bar"
    except IbHomeVmException as e :
        raise

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/configurex --foo=bar"
        assert False
    except IbHomeVmValueError as e :
        pass

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/config --foo=bar"
        assert False
    except IbHomeVmValueError as e :
        pass

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
