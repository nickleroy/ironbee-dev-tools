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
import shlex

from ib.util.version     import *
from ib.build.exceptions import *

class _DataItem( object ) :
    """
    An archive data item.  This is a immutable object used to describe the meta-data
    of a data item.
    """
    def __init__( self, name, required, _type,
                  validator=None, getfn=None, to_str=None, from_str=None ) :
        assert validator is None  or  callable(validator)
        self._name = name
        self._required = required
        self._type = _type
        self._validator = validator
        self._getfn = getfn
        self._to_str = to_str
        self._from_str = from_str
    Name      = property( lambda self : self._name )
    Required  = property( lambda self : self._required )
    Validator = property( lambda self : self._validator )
    GetFn     = property( lambda self : self._getfn )
    ToStr     = property( lambda self : self._to_str )
    FromStr   = property( lambda self : self._from_str )


class _ArchiveRecord( object ) :
    """
    An archive record.
    """
    def __init__( self, name, filename, destdir ) :
        self._name = name
        self._filename = filename
        self._destdir = destdir
    Name     = property( lambda self : self._name )
    FileName = property( lambda self : self._filename )
    DestDir  = property( lambda self : self._destdir )
    def __str__( self ) :
        return '"{r.Name}": "{r.FileName}" -> "{r.DestDir}"'.format(r=self)

def _StrToList( value ) :
    if type(value) in (list, tuple, None) :
        return list(value)
    elif type(value) == str :
        if value[0] == '(' and value[-1] == ')'  or  value[0] == '[' and value[-1] == ']' :
            return value[1:-1].split("', '")
        else :
            return shlex.split(value)
    else :
        raise ValueError

def _StrToBool( value ) :
    if type(value) is bool :
        return value
    elif type(value) == str :
        return value.startswith( ('T','t','Y','y', '1') )
    else :
        raise ValueError

# Build Build Archive
class IbBuildArchive( object ) :

    _version_re     = re.compile(r'\d+\.\d+(?:\.\d+)?$')
    _commit_re      = re.compile(r'[0-9a-fA-F]{8,40}$')
    _ats_version_re = re.compile(r'\d+(\.(\d+|x)){1,3}(?:-\w+)?$')

    _item_names = dict( [ (p.Name, p) for p in (
        _DataItem( 'ArchiveDirectory',      True,  str ),
        _DataItem( 'Name',                  True,  str ),
        _DataItem( 'Labels',                False, list,
                   from_str=_StrToList ),
        _DataItem( 'TimeStamp',             True,  float ),
        _DataItem( 'BuildHost',             False, str ),
        _DataItem( 'QualysLocal',           True,  str ),
        _DataItem( 'IronBeeVersion',        True,  IbVersion ),
        _DataItem( 'IronBeeGitBranch',      True,  str ),
        _DataItem( 'IronBeeGitCommit',      False, str,
                   validator=lambda cls,value : cls._commit_re.match(value) ),
        _DataItem( 'Architecture',          True,  str ),
        _DataItem( 'Bits',                  True,  int ),
        _DataItem( 'EtcInGitBranch',        True,  str ),
        _DataItem( 'EtcInGitCommit',        False, str,
                   lambda cls,value : cls._commit_re.match(value) ),
        _DataItem( 'EtcInGitRepo',          False, str ),
        _DataItem( 'BuildConfig',           False, list,
                   validator=lambda cls,value : value is None or value[0].endswith("configure"),
                   from_str=_StrToList ),
        _DataItem( 'Compiler',              True,  str ),
        _DataItem( 'GccVersion',            True,  str,
                   lambda cls,value : cls._version_re.match(value) ),
        _DataItem( 'ClangVersion',          False, str,
                   validator=lambda cls,value : cls._version_re.match(value) ),
        _DataItem( 'ClangThreadSanitizer',  False, bool,
                   from_str=_StrToBool ),
        _DataItem( 'CFlags',                False, str ),
        _DataItem( 'CxxFlags',              False, str ),
        _DataItem( 'AtsVersion',            False, str,
                   validator=lambda cls,value : cls._ats_version_re.match(value) ),
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
            raise IbBuildDataError( 'Attempt to check unknown attribute "{0}"'.format(name) )

    def __setattr__( self, name, value ) :
        if name.startswith('_'):
            super(IbBuildArchive, self).__setattr__(name, value)
            return
        elif name not in self._item_names :
            raise IbBuildDataError( 'Attempt to set unknown attribute "{0}"'.format(name) )
        elif value is None :
            return
        try :
            item = self._item_names[name]
            if item.FromStr is not None :
                converted = item.FromStr( value )
            else :
                converted = item._type( value )
            if not self._CheckValue( name, converted, item ) :
                raise ValueError
            self._items[name] = converted
        except ( ValueError, IbBuildDataError ) :
            raise IbBuildValueError( 'Attempt to set "{0}" to invalid value "{1}"'.
                                         format(name, str(value)) )

    def __getattr__( self, name ) :
        if name not in self._item_names :
            raise IbBuildDataError( 'Attempt to access unknown attribute "{0}"'.format(name) )
        return self._items.get(name, None)

    def Get( self, name, default=None ) :
        if name not in self._item_names :
            raise IbBuildDataError( 'Attempt to access unknown attribute "{0}"'.format(name) )
        return self._items.get(name, default)

    # Vm time stamp format for strftime()
    _TimeStampFormat = '%Y.%m.%d.%H.%M.%S'
    @classmethod
    def FormatTime( cls, when ) :
        s1 = time.strftime( cls._TimeStampFormat, time.localtime(when) )
        s2 = '{:.02f}'.format(when).split('.')[1]
        return s1+'.'+s2

    TimeString = property( lambda self : self.FormatTime(self.TimeStamp) )

    def AddArchive( self, name, filename, destdir ) :
        rec = _ArchiveRecord( name, filename, destdir )
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
                raise IbBuildException( "Missing item: "+name )
            elif value is not None  and  item.Validator is not None :
                item.Validator(self, value)

    def GenerateArchiveData( self ) :
        lines = []
        self.Validate( )
        for name,value in sorted(self._items.items()) :
            if value is not None :
                lines.append( name+'='+str(value) )
        for rec in self._archives :
            lines.append( "Archive:{r.Name}={r.FileName},{r.DestDir}".format(r=rec) )
        return lines

    def PrintSummary( self ) :
        lines = self.GenerateArchiveData( )
        print '==='
        for line in lines :
            print line
        print '==='

    def WriteArchiveData( self, archive_dir ) :
        lines = self.GenerateArchiveData( )
        path = os.path.join( archive_dir, 'archives.txt' )
        with open(path, 'w') as fp :
            for line in lines :
                print >>fp, line

    _archive_rec_re = re.compile( r'Archive:([\w\-]+)$' )
    def ReadArchiveData( self, archive_dir ) :
        path = os.path.join( archive_dir, 'archives.txt' )
        if not os.path.isfile( path ) :
            return False
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
                    rec = _ArchiveRecord( m.group(1), filename, destdir )
                    self._archives.append( rec )
                else :
                    self.__setattr__(name, value)
            return True
        except IOError as e :
            raise IbBuildException( 'Failed to read archive file "{0}": {1}'.format(path, e) )

    @classmethod
    def CreateFromFile( cls, archive_path ) :
        try :
            vm = cls( )
            if vm.ReadArchiveData( archive_path ) :
                vm.Validate( )
                return vm
            else :
                return None
        except IbBuildException as e :
            print e
            return None

    def __str__( self ) :
        return str(self._items)


class IbBuildArchiveSet( object ) :
    def __init__( self, archives_dir ) :
        self._archives_dir = archives_dir
        self._archives = [ ]
    ArchivesDir = property( lambda self : self._archives_dir )

    def ReadAll( self ) :
        for name in os.listdir( self._archives_dir ) :
            full = os.path.join(self._archives_dir, name)
            if not os.path.isdir( full ) :
                continue
            vm = IbBuildArchive.CreateFromFile( full )
            if vm is not None :
                self._archives.append( vm )

    def Archives( self, filter=None ) :
        for archive in self._archives :
            if filter is None or filter(archive) :
                yield archive
        return


if __name__ == "__main__" :
    data = IbBuildArchive( )
    try :
        data.foo = 'abc'
        assert False
    except IbBuildDataError as e :
        pass

    try :
        now = time.time()
        s = IbBuildBuild.FormatTime( now )
        data.TimeStamp = now
        time.sleep(0.2)
        assert data.TimeStamp == now
        assert data.TimeString == s
    except IbBuildDataError as e :
        raise

    try :
        data.IronBeeVersion = IbVersion('0.11.3')
        assert type(data.IronBeeVersion) == IbVersion
        assert str(data.IronBeeVersion) == '0.11.3'
    except IbBuildError as e :
        raise

    try :
        data.IronBeeVersion = '0.11.3'
    except IbBuildException as e :
        pass

    try :
        data.IronBeeGitBranch = "master"
        assert data.IronBeeGitBranch == "master"
    except IbBuildException as e :
        raise

    try :
        data.IronBeeGitCommit = "7a98ec3b"
        assert data.IronBeeGitCommit == "7a98ec3b"
    except IbBuildException as e :
        raise

    try :
        data.IronBeeGitCommit = "7a98ec3bx"
        assert False
    except IbBuildValueError as e :
        pass

    try :
        data.EtcInGitCommit = "520c3a59bd5937e98d650c440337345317744cc0"
        assert data.EtcInGitCommit == "520c3a59bd5937e98d650c440337345317744cc0"
    except IbBuildException as e :
        raise

    try :
        data.BuildConfig = "/build/nick/devel/qualys/ib/configure"
        assert data.BuildConfig == "/home/nick/devel/qualys/ib/configure"
    except IbBuildException as e :
        raise

    try :
        data.BuildConfig = "./configure"
        assert data.BuildConfig == "./configure"
    except IbBuildException as e :
        raise

    try :
        data.BuildConfig = "./xconfigure"
        assert False
    except IbBuildValueError as e :
        pass

    try :
        data.BuildConfig = "configure"
        assert data.BuildConfig == "configure"
    except IbBuildException as e :
        raise

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/configure --foo=bar"
        assert data.BuildConfig == "/home/nick/devel/qualys/ib/configure --foo=bar"
    except IbBuildException as e :
        raise

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/configurex --foo=bar"
        assert False
    except IbBuildValueError as e :
        pass

    try :
        data.BuildConfig = "/home/nick/devel/qualys/ib/config --foo=bar"
        assert False
    except IbBuildValueError as e :
        pass

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
