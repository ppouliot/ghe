#!/bin/bash
#
# Enable, disable and query the status of a remote GitHub enterprise maintenance
# mode. Requires ssh-keys for the individual commands to be present.
#
# ~/.ghe/keys/ghe-maintenance-query should be a file containing the private key
# that has been given rights to run the `ghe-maintenance --query` command.
#
# ~/.ghe/keys/ghe-maintenance-on should be a file containing the private key
# that has been given rights to run the `ghe-maintenance --set` command.
#
# ~/.ghe/keys/ghe-maintenance-off should be a file containing the private key
# that has been given rights to run the `ghe-maintenance --unset` command.
#
# The public keys for these private keys should be added to the GHE server by
# prefixing it with the command directive. For more information, please read
# https://en.wikibooks.org/wiki/OpenSSH/Client_Configuration_Files#.7E.2F.ssh.2Fauthorized_keys
#
# Example public key format as saved on GHE:
#
# command="ghe-maintenance --query" MIICXAIBAA...Q5mBk= maintenance query

show_help() {
  local ret
  ret=`sed -n '6,21p' < ghe/commands/ghe-maintenance.sh | sed 's/^.//'`
  echo "There was an error running the maintenance command."
  echo
  echo "${ret}"
  echo
  exit 1
}

[ -f $HOME/.ghe/keys/ghe-maintenance-query ] || show_help
[ -f $HOME/.ghe/keys/ghe-maintenance-on ] || show_help
[ -f $HOME/.ghe/keys/ghe-maintenance-off ] || show_help


maintenance() {
  cmd=$1
  local conn="ssh -p 122 admin@git.generalassemb.ly -i ${HOME}/.ghe/keys"
  local ret
  ret=`${conn}/ghe-maintenance-${cmd} 2> /dev/null`
  res=$?
}

maintenance_status() {
  maintenance query
  if [ $res == 0 ]; then
    echo "Maintenance mode is currently active."
  else
    echo "Maintenance mode is currently inactive."
  fi
}

maintenance_enable() {
  echo "Enabling maintenance mode..."
  maintenance on
  maintenance_status
}

maintenance_disable() {
  echo "Disabling maintenance mode..."
  maintenance off
  maintenance_status
}

case "$1" in
  on)
    maintenance_enable
    ;;
  off)
    maintenance_disable
    ;;
  *)
    maintenance_status
    ;;
esac
