#!/bin/bash
if [ $# -eq 1 ]; then
  channel=$1
else
  echo "usage : $0 channel_name"
  echo "         channel_name list"
  echo "           ABC RADIO: ABC"
  echo "           MBS RADIO: MBS"
  echo "           OBC RADIO: OBC"
  echo "           FM COCOLO: CCL"
  echo "           FM802: 802"
  echo "           FM OH: FMO"
  echo "           RADIONIKKEI: RN1"
  echo "           RADIONIKKEI2: RN2"
  echo "           Kiss FM KOBE: KISSFMKOBE"
  echo "           HOUSOU-DAIGAKU: HOUSOU-DAIGAKU"
  exit 1
fi

pid=$$
date=`date '+%Y-%m-%d-%H:%M'`
playerurl=http://radiko.jp/apps/js/flash/myplayer-release.swf
outdir="$HOME/.cache/radio"
playerfile="${outdir}/player.swf"
keyfile="${outdir}/authkey.png"
auth1_fms_file="${outdir}/auth1_fms_${pid}"
auth2_fms_file="${outdir}/auth2_fms_${pid}"
channel_file="${outdir}/${channel}.xml"
mkdir -p ${outdir}

#
# get player
#
if [ ! -f $playerfile ]; then
   curl -o $playerfile $playerurl

  if [ $? -ne 0 ]; then
    echo "failed to get player"
    exit 1
  fi
fi

#
# get keydata (need swftool)
#
if [ ! -f $keyfile ]; then
  swfextract -b 12 $playerfile -o $keyfile

  if [ ! -f $keyfile ]; then
    echo "failed to get keydata"
    exit 1
  fi
fi

if [ -f ${auth1_fms_file} ]; then
  rm -f ${auth1_fms_file}
fi

#
# access auth1_fms
#
# curl -d "" -o ${auth1_fms_file} -H "X-Radiko-App: pc_ts" -H "X-Radiko-App-Version: 4.0.0" -H "X-Radiko-Device: pc" -H "X-Radiko-User: test-stream" https://radiko.jp/v2/api/auth1_fms


#
# access auth1_fms
#
wget -q \
     --header="pragma: no-cache" \
     --header="X-Radiko-App: pc_ts" \
     --header="X-Radiko-App-Version: 4.0.0" \
     --header="X-Radiko-User: test-stream" \
     --header="X-Radiko-Device: pc" \
     --post-data='\r\n' \
     --no-check-certificate \
     --save-headers \
     -O ${auth1_fms_file} \
     https://radiko.jp/v2/api/auth1_fms

if [ $? -ne 0 ]; then
  echo "failed auth1 process"
  exit 1
fi

#
# get partial key
#
authtoken=`perl -ne 'print $1 if(/x-radiko-authtoken: ([\w-]+)/i)' ${auth1_fms_file}`
offset=`perl -ne 'print $1 if(/x-radiko-keyoffset: (\d+)/i)' ${auth1_fms_file}`
length=`perl -ne 'print $1 if(/x-radiko-keylength: (\d+)/i)' ${auth1_fms_file}`
partialkey=`dd if=$keyfile bs=1 skip=${offset} count=${length} 2> /dev/null | base64`

echo "authtoken: ${authtoken} offset: ${offset} length: ${length} partialkey: ${partialkey}"

rm -f ${auth1_fms_file}

if [ -f ${auth2_fms_file} ]; then
  rm -f ${auth2_fms_file}
fi

#
# access auth2_fms
#
wget -q \
     --header="pragma: no-cache" \
     --header="X-Radiko-App: pc_ts" \
     --header="X-Radiko-App-Version: 4.0.0" \
     --header="X-Radiko-User: test-stream" \
     --header="X-Radiko-Device: pc" \
     --header="X-Radiko-Authtoken: ${authtoken}" \
     --header="X-Radiko-Partialkey: ${partialkey}" \
     --post-data='\r\n' \
     --no-check-certificate \
     -O ${auth2_fms_file} \
     https://radiko.jp/v2/api/auth2_fms

if [ $? -ne 0 -o ! -f ${auth2_fms_file} ]; then
  echo "failed auth2 process"
  exit 1
fi

areaid=`perl -ne 'print $1 if(/^([^,]+),/i)' ${auth2_fms_file}`
echo "areaid: $areaid"

echo "authentication success"

rm -f ${auth2_fms_file}

#
# get stream-url
#

if [ -f ${channel_file} ]; then
  rm -f ${channel_file}
fi

wget -q "http://radiko.jp/v2/station/stream/${channel}.xml" -O ${channel_file}

stream_url=`echo "cat /url/item[1]/text()" | xmllint --shell ${channel_file} | tail -2 | head -1`
url_parts=(`echo ${stream_url} | perl -pe 's!^(.*)://(.*?)/(.*)/(.*?)$/!$1://$2 $3 $4!'`)

rm -f ${channel_file}

rtmpdump -v \
         -r ${url_parts[0]} \
         --app ${url_parts[1]} \
         --playpath ${url_parts[2]} \
         -W $playerurl \
         -C S:"" -C S:"" -C S:"" -C S:$authtoken \
         --buffer 1000 -o - \
         | cvlc -
