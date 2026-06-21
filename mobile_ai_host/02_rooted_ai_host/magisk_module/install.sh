#!/system/bin/sh
# install.sh — Magisk module installer (runs in Magisk's installer context)
# Just copies files into the module dir. Magisk handles the rest.

SKIPUNZIP=0
ui_print "- AI Host Service Stripper"
ui_print "- Preparing module..."

# Set permissions on the service script
set_perm $MODPATH/service.sh 0 0 0755
set_perm $MODPATH/post-fs-data.sh 0 0 0755
set_perm $MODPATH/system/etc/init/ai_host.rc 0 0 0644

ui_print "- Done. Reboot to activate."
