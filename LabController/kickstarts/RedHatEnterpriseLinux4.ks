#if $varExists('sysprofile')
#set listed_snippet_profiles = $getVar('sysprofile','').split(';')
#for $snippet_profile in $listed_snippet_profiles
# Snippet Profile: $snippet_profile
$SNIPPET($snippet_profile)
#end for
#else
$SNIPPET("install_method")

#if $getVar('system_name', '') != '' and $getVar('manual', 'False') == 'False'
authconfig  --enableshadow  --enablemd5
# System bootloader configuration
bootloader --location=mbr #slurp
#if $getVar('kernel_options_post','') != ''
    --append="$kernel_options_post"
#end if

$getVar('mode', '')

$SNIPPET("network")
## Firewall configuration
## firewall in kickstart metadata will enable the firewall
## firewall=22:tcp,80:tcp will enable the firewall with ports 22 and 80 open.
## always allow port 12432 so that beah harness will support multihost
firewall #slurp
#if $getVar('firewall', 'disabled') == 'disabled':
--disabled
#else
--enabled --port=12432:tcp #slurp
#if $getVar('firewall', '') != '':
,$getVar('firewall')
#end if
#end if

# System keyboard
keyboard $getVar('keyboard', 'us')
# System language
lang $getVar('lang','en_US.UTF-8')
langsupport --default $getVar('lang', 'en_US.UTF-8') $getVar('lang','en_US.UTF-8')
$yum_repo_stanza
reboot
#Root password
rootpw --iscrypted $getVar('password', $default_password_crypted)
# SELinux configuration
selinux --$getVar('selinux', 'enforcing')

#if $getVar('skipx','') != ''
skipx
#end if

# System timezone
timezone  $getVar('timezone', 'America/New_York')
# Install OS instead of upgrade
install

$SNIPPET("rhts_scsi_ethdevices")
$SNIPPET("rhts_partitions")
$SNIPPET("RedHatEnterpriseLinux4")
$SNIPPET("system")

%packages --resolvedeps --ignoremissing
## If packages variable is set add additional packages to this install
## packages=httpd:selinux:kernel
#if $getVar('packages', '') != ''
$SNIPPET("rhts_packages")
#else
@development-tools
@development-libs
@ office
@ dialup
@ sound-and-video
@ editors
@ admin-tools
@ printing
@ base-x
@ gnome-desktop
@ graphics
@ games
@ text-internet
@ graphical-internet
@ compat-arch-support
e2fsprogs
lvm2
#end if ## %packages

#end if ## manual

#end if ## sysprofile snippet

%pre --log=/dev/console
$SNIPPET("rhts_pre")
$SNIPPET("RedHatEnterpriseLinux4_pre")
$SNIPPET("system_pre")

%post --log=/dev/console
$SNIPPET("rhts_post")
$SNIPPET("RedHatEnterpriseLinux4_post")
$SNIPPET("system_post")

#if $getVar('ks_appends', '') != '':
$SNIPPET("ks_appends")
#end if