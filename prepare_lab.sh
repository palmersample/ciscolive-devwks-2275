#!/bin/bash

ERROR_COUNT=0
ERROR_MESSAGES=""

[ ! -d "./ssh" ] && mkdir ./ssh
NETCONF_SSH_CONFIG_FILE="ssh/netconf_ssh_config"
SSH_CONFIG_FILE="ssh/ssh_config"

TIMEOUT_CMD=`which timeout`
if [ $? -eq 0 ]; then
  TIMEOUT_CMD="${TIMEOUT_CMD} 5 "
else
  TIMEOUT_CMD=""
fi

test_proxy()
{
  declare PROXY_HOST="proxy.${DNS_DOMAIN}"
  printf "%40s" "Proxy status: "
  PROXY_CONNECT_RESULT=$(echo "" | ${TIMEOUT_CMD}openssl s_client -connect ${PROXY_HOST}:443 -tls1_2 2>&1 > /dev/null)
  if [ $? -ne 0 ] ; then
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- Unable to contact the proxy server.\n"
    echo "FAIL"
  else
    echo "OK"
  fi
}

test_vault()
{
  INIT_TARGET="true"
  SEAL_TARGET="false"
  UI_TARGET=200

  printf "%40s" "Vault Web UI status: "
  VAULT_UI_RESULT=$(${TIMEOUT_CMD}curl -s -o /dev/null -w "%{http_code}" "${VAULT_URL}/ui/vault/auth?with=token")

  if [ "x${VAULT_UI_RESULT}" = "x${UI_TARGET}" ]; then
    echo "OK"
  else
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- The Vault UI is not accessible.\n"
    echo "FAIL"
  fi

  printf "%40s" "Vault API status: "
  VAULT_API_RESULT=$(${TIMEOUT_CMD}curl -fsv \
    --header "X-Vault-Token: $VAULT_TOKEN" \
    "${VAULT_URL}/v1/sys/seal-status" 2>&1)

  if [ $? -ne 0 ] ; then
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- The Vault API is not accessible.\n"
    echo "FAIL"
  else
    echo "OK"

    INIT_STATUS=$(grep -o '"'"initialized"'"\s*:\s*\(true\|false\)' \
      <<<${VAULT_API_RESULT} | \
      awk -F: '{ print $2 }'
    )

    SEAL_STATUS=$(grep -o '"'"sealed"'"\s*:\s*\(true\|false\)' \
      <<<${VAULT_API_RESULT} | \
      awk -F: '{ print $2 }'
    )

    printf "%40s" "Vault initialization status: "
    if [ "x${INIT_STATUS}" = "x${INIT_TARGET}" ]; then
      echo "OK"
    else
      ERROR_COUNT=${ERROR_COUNT+1}
      ERROR_MESSAGES="${ERROR_MESSAGES}\t- The Vault server is not initialized.\n"
      echo "FAIL"
    fi

    printf "%40s" "Vault seal status: "
    if [ "x${SEAL_STATUS}" = "x${SEAL_TARGET}" ]; then
      echo "OK"
    else
      ERROR_COUNT=${ERROR_COUNT+1}
      ERROR_MESSAGES="${ERROR_MESSAGES}\t- Vault secrets are are not accessible.\n"
      echo "FAIL"
    fi

  fi
}

test_netbox()
{
  NETBOX_UI_TARGET=200

  printf "%40s" "NetBox UI status: "
  NETBOX_UI_RESULT=$(${TIMEOUT_CMD}curl -s -o /dev/null -w "%{http_code}" "${NETBOX_URL}")
  if [ "x${NETBOX_UI_RESULT}" = "x${NETBOX_UI_TARGET}" ]; then
    echo "OK"
  else
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- The NetBox UI is not accessible.\n"
    echo "FAIL"
  fi

  printf "%40s" "NetBox API status: "
  NETBOX_API_RESULT=$(${TIMEOUT_CMD}curl -fsv \
    "${NETBOX_URL}/api/status/" 2>&1)

  if [ $? -ne 0 ] ; then
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- The NetBox API is not accessible.\n"
    echo "FAIL"
  else
    echo "OK"
  fi
}

test_router()
{
  declare PROXY_HOST="proxy.${DNS_DOMAIN}"
  declare WLC_HOST="pod${POD_NUMBER}-wlc.${DNS_DOMAIN}"
  declare WLC_URL="https://${WLC_HOST}"
  # Expect an "Unauthorized" result
  RESTCONF_TARGET=401

  printf "%40s" "IOSXE SSH Status: "
  SSH_PROXY_RESULT=$(${TIMEOUT_CMD}ssh \
    -o ProxyCommand="openssl s_client -quiet -servername ${WLC_HOST} -connect ${PROXY_HOST}:8000" \
    -o 'BatchMode=yes' \
    -o 'ConnectionAttempts=1' \
    -o "StrictHostKeyChecking=no" \
    dummy@${WLC_HOST} -p 8000 2>&1 > /dev/null
  )
  SSH_STATUS=$(grep -i "permission denied" <<<${SSH_PROXY_RESULT})
  if [ $? -ne 0 ]; then
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- IOSXE SSH is not accessible.\n"
    echo "FAIL"
  else
    echo "OK"
  fi

  printf "%40s" "IOSXE NETCONF Status: "
  NETCONF_PROXY_RESULT=$(${TIMEOUT_CMD}ssh \
    -o ProxyCommand="openssl s_client -quiet -servername ${WLC_HOST} -connect ${PROXY_HOST}:8300" \
    -o 'BatchMode=yes' \
    -o 'ConnectionAttempts=1' \
    -o "StrictHostKeyChecking=no" \
    dummy@${WLC_HOST} \
    -p 830 NETCONF 2>&1 > /dev/null)
  # echo ${NETCONF_PROXY_RESULT}
  NETCONF_STATUS=$(grep -i "permission denied" <<<${NETCONF_PROXY_RESULT})
  if [ $? -ne 0 ]; then
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- IOSXE NETCONF is not accessible.\n"
    echo "FAIL"
  else
    echo "OK"
  fi

  printf "%40s" "IOSXE RESTCONF Status: "
  RESTCONF_RESULT=$(${TIMEOUT_CMD}curl -s -o /dev/null -w "%{http_code}" \
    "${WLC_URL}/restconf"
  )
  if [ "x${RESTCONF_RESULT}" = "x${RESTCONF_TARGET}" ]; then
    echo "OK"
  else
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- IOSXE RESTCONF is not accessible.\n"
    echo "FAIL"
  fi
}

generate_ssh_config()
{
  declare PROXY_HOST="proxy.${DNS_DOMAIN}"
  printf "%40s" "NETCONF proxy: "
  # Generate NETCONF SSH Proxy Config file
  echo "Host *.${DNS_DOMAIN}" > ${NETCONF_SSH_CONFIG_FILE}
  echo "  ProxyCommand openssl s_client -quiet -servername %h -connect ${PROXY_HOST}:8300" >> ${NETCONF_SSH_CONFIG_FILE}

  if [ -f ${NETCONF_SSH_CONFIG_FILE} ]; then
    echo "OK"
  else
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- NETCONF SSH Proxy config not created.\n"
    echo "FAIL"
  fi

  printf "%40s" "SSH proxy: "
  # Generate SSH Proxy Config file
  echo "Host *.${DNS_DOMAIN}" > ${SSH_CONFIG_FILE}
  echo "  ProxyCommand openssl s_client -quiet -servername %h -connect ${PROXY_HOST}:8000" >> ${SSH_CONFIG_FILE}

  if [ -f ${SSH_CONFIG_FILE} ]; then
    echo "OK"
  else
    ERROR_COUNT=${ERROR_COUNT+1}
    ERROR_MESSAGES="${ERROR_MESSAGES}\t- SSH Proxy config not created.\n"
    echo "FAIL"
  fi

}

echo "GET READY FOR YOUR CISCO LIVE WORKSHOP EXPERIENCE! :)"
echo ""

echo -n "What is your pod number? "
read POD_NUMBER

[ -f workshop.env ] && . ./workshop.env

VAULT_URL="https://pod${POD_NUMBER}-vault.${DNS_DOMAIN}"
NETBOX_URL="https://pod${POD_NUMBER}-netbox.${DNS_DOMAIN}"

echo ""
echo "************************************************************************"

echo ""
echo "TEST 1: Checking connectivity to the proxy for Pod ${POD_NUMBER}"
test_proxy

#echo ""
#echo "TEST 2: Checking connectivity to Hashicorp Vault in Pod ${POD_NUMBER}:"
#test_vault

echo ""
echo "TEST 2: Checking connectivity to NetBox in Pod ${POD_NUMBER}:"
test_netbox

echo ""
echo "TEST 3: Checking connectivity to IOSXE in Pod ${POD_NUMBER}:"
test_router

echo ""
echo "SETUP: Generate SSH configuration files for Pod ${POD_NUMBER}"
generate_ssh_config

echo ""
if [ ${ERROR_COUNT} -gt 0 ]; then
  echo "THERE WERE ERRORS IN SETUP TESTING:"
  printf "${ERROR_MESSAGES}\n"
  echo "\tPlease ask your proctor for assistance!"
else
  echo "ALL SETUP TASKS OK - Time to have some automation fun!"
  export VAULT_ADDR=${VAULT_URL}
  export VAULT_TOKEN=${VAULT_TOKEN}
  export NETBOX_URL=${NETBOX_URL}
  export WLC_HOST="pod${POD_NUMBER}-wlc.${DNS_DOMAIN}"
  export WLC_USERNAME=${WLC_USERNAME}
  export WLC_PASSWORD=${WLC_PASSWORD}

fi

echo ""
