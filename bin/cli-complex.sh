#!/bin/sh
DEVEL=${HOME}/devel
ETC=${DEVEL}/etc
DATA=${DEVEL}/data
VAR=${DEVEL}/var
TMP=${DEVEL}/tmp

if test "$IBROOT" = "" ; then
  IBROOT=${DEVEL}/ib-gcc
fi
if test "$IBBUILD" = "" ; then
  IBBUILD="${IBROOT}/build"
fi

ETC_IB=${ETC}/ironbee
DATE=`date '+%Y%m%d.%H%M%S'`
LOG=${VAR}/log/ironbee
LOGBACK=${VAR}/log/ironbee.bak

REQFILE=${DATA}/skip2/req-0319/03198-40315-0000.raw
RSPFILE=${DATA}/skip2/rsp-0319/03198-40315-0000.raw
# REQFILE=${DATA}/marcin-2012-05-15/15076-1.req
# RSPFILE=${DATA}/marcin-2012-05-15/15076.resp
# REQFILE=${DATA}/req-data/req.raw
# RSPFILE=${DATA}/req-data/rsp.raw
# REQFILE=${DATA}/brian/2012-06-14.req
# RSPFILE=${DATA}/brian/2012-06-14.rsp
# REQFILE=${DATA}/tmp/2012-07-05.req
# RSPFILE=${DATA}/tmp/2012-07-05.rsp
# REQFILE=${DATA}/http-0.9-req.txt
# RSPFILE=${DATA}/http-0.9-rsp.txt
# REQFILE=${TMP}/segv/15008.req
# RSPFILE=${TMP}/segv/15008.rsp

#REQFILE=${TMP}/skipfishVmoth.pcap-03198-192.168.2.3-40315-192.168.2.6-80.request.0000.raw

REMOTE_IP=128.105.121.53
#REMOTE_PORT=80
#LOCAL_IP=192.168.1.1
#LOCAL_PORT=1234

if [ "${REMOTE_IP}" != "" ] ; then
  ADDR_ARGS="${ADDR_ARGS} --remote-ip ${REMOTE_IP}"
fi
if [ "${REMOTE_PORT}" != "" ] ; then
  ADDR_ARGS="${ADDR_ARGS} --remote-port ${REMOTE_PORT}"
fi
if [ "${LOCAL_IP}" != "" ] ; then
  ADDR_ARGS="${ADDR_ARGS} --local-ip ${LOCAL_IP}"
fi
if [ "${LOCAL_PORT}" != "" ] ; then
  ADDR_ARGS="${ADDR_ARGS} --local-port ${LOCAL_PORT}"
fi

CONF="--config ${ETC_IB}/cli.conf"
REQ="--request-file ${REQFILE}"
RSP="--response-file ${RSPFILE}"
MISC_ARGS="--dump tx-full"
CLI_ARGS="${CONF} ${REQ} ${RSP} ${ADDR_ARGS} ${MISC_ARGS}"
CLI="${IBBUILD}/cli/.libs/ibcli"


OUT=${LOG}/ibcli.out
ERR=${LOG}/ibcli.err
IBLOG=${LOG}/ibcli.log
mkdir ${LOGBACK}
mv ${LOG} ${LOGBACK}/ironbee-${DATE}
mkdir ${LOG}
make -C ${ETC_IB}.in
CMD="${CLI} ${CLI_ARGS}"
echo ${CMD} "> ${OUT}"
${CMD} > ${OUT} 2>${ERR}
less ${OUT} ${REQFILE} ${RSPFILE} ${ERR} ${IBLOG}
