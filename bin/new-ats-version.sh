#! /bin/sh
for f in etc tmp var ; do 
  if [ -d $f ] ; then
    mv $f $f-release
  fi
  ln -s ../../$f .
done
