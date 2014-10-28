#!/usr/bin/env python
# Nick's confgen RC file for IronBee, etc.
from confgen.rc.base import *
from confgen.rc.gcc import *
from confgen.rc.clang import *

from ib.build.base import *

class _IbRc( object ) :
    def __init__( self ) :
        self._base = ConfGenBaseRc( "base" )
        self._config = None
        self._info = None
        self._build = None
        print self._base.Vars()

    def _Var( self, name, default=None ) :
        return self._base.GetVar(name, default)

    def Setup( self ) :
        compiler = self._Var("compiler","gcc")
        if compiler == "gcc" :
            self._config = IbConfGenGcc( )
        elif compiler == "clang" :
            self._config = IbConfGenClang( )
        elif compiler == "doxygen" :
            self._config = IbConfGenDoxygen( )

        build = self._Var("build","IronBee")
        self._info = IbBuildInfo( self._Var("Build","IronBee"),
                                  self._Var("type","devel") )
        self._build = IbBuild( self._config, self._info )
        self._build.Setup()
        self._build.SetupIronBee( )
        self._build.Finish( )

_rc = _IbRc()
_rc.Setup()

### Local Variables: ***
### py-indent-offset:4 ***
### python-indent:4 ***
### python-continuation-offset:4 ***
### tab-width:4  ***
### End: ***
