#!/bin/sh
DEVEL=${HOME}/devel
BUILD=${DEVEL}/build
ETC=${DEVEL}/etc
ETC_IB=${ETC}/ironbee
DATA=${DEVEL}/data
VAR=${DEVEL}/var
TMP=${DEVEL}/tmp
ETC_IN=${DEVEL}/etc.in
ETC_IN_IB=${ETC_IN}/ironbee

if test "$IBBUILD" = "" ; then
  IBBUILD="${BUILD}/gcc-std"
fi


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


#REMOTE_IP=128.105.121.53
REMOTE_IP=127.0.1.1
#REMOTE_PORT=80
#LOCAL_IP=192.168.1.1
#LOCAL_PORT=1234
HOST=site1.nick.com
REFERER=-

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
if [ "${HOST}" != "" ] ; then
  HEADERS="${HEADERS} --request-header Host:${HOST}"
fi
if [ "${REFERER}" == "-" ] ; then
  HEADERS="${HEADERS} --request-header -Referer:"
elif [ "${REFERER}" != "" ] ; then
  HEADERS="${HEADERS} --request-header Referer:${REFERER}"
fi

CONF="--config ${ETC_IB}/cli.conf"
REQ="--request-file ${REQFILE}"
RSP="--response-file ${RSPFILE}"
MISC_ARGS="--dump all ${HEADERS}"
#MISC_ARGS="--dump tx-full ${HEADERS}"
CLI_ARGS="${CONF} ${REQ} ${RSP} ${ADDR_ARGS} ${MISC_ARGS}"
CLI="${IBBUILD}/install/bin/ibcli"


OUT=${LOG}/ibcli.out
ERR=${LOG}/ibcli.err
IBLOG=${LOG}/ibcli.log
mkdir ${LOGBACK}
mv ${LOG} ${LOGBACK}/ironbee-${DATE}
mkdir ${LOG}
make -C ${ETC_IN_IB}
CMD="${CLI} ${CLI_ARGS}"
echo ${CMD} "> ${OUT}"
${CMD} > ${OUT} 2>${ERR}
less ${OUT} ${REQFILE} ${RSPFILE} ${ERR} ${IBLOG}
