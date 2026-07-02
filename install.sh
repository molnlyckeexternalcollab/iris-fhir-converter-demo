#!/bin/bash
# Usage install.sh [instanceName] [password] [namespace]

die () {
    echo >&3 "$@"
    exit 1
}

[ "$#" -eq 3 ] || die "Usage install.sh [instanceName] [password] [Namespace]"

DIR=$(dirname $0)
if [ "$DIR" = "." ]; then
DIR=$(pwd)
fi

instanceName=$1
password=$2
NameSpace=$3

# Installer source (Installer.*.cls)
ClassImportDir=$DIR/Misc
# Source dir to install by source installer
DirSrc=$DIR


echo "+-------------------------------------------------+"
echo "|              Now it's show time !               |"
echo "|         iris session going in action            |"
echo "+-------------------------------------------------+"
irissession $instanceName -U USER <<EOF
sys
$2
WRITE "[ OK ] Start a terminal session for the instance $instanceName"

ZN "USER"
WRITE "[ OK ] Set USER namespace as current namespace"


WRITE "Install InterSystems Package Manager - IPM" 
SET version="latest"
SET r=##class(%Net.HttpRequest).%New()
SET r.Server="pm.community.intersystems.com"
SET r.SSLConfiguration="ISC.FeatureTracker.SSL.Config"
SET tSc = r.Get("/packages/zpm/"_version_"/installer")
WRITE:(tSc'=1) "[ FAIL ] Get /packages/zpm/"_version_"/installer"_\$System.Status.GetErrorText(tSc)
DO:(tSc'=1) \$SYSTEM.Process.Terminate(,1),h
SET tSc = \$SYSTEM.OBJ.LoadStream(r.HttpResponse.Data,"c")
WRITE:(tSc'=1) "[ FAIL ] LoadStream: "_\$System.Status.GetErrorText(tSc)
DO:(tSc'=1) \$SYSTEM.Process.Terminate(,1),h
WRITE "[ OK ] Install InterSystems Package Manager - IPM"

WRITE "Enable the community package registry without the rest of the legacy behavior"
zpm "repo -r -n registry -url https://pm.community.intersystems.com/ -user "" -pass """

WRITE "Move in package manager mode"
zpm "install webterminal"
zpm "install fhir-portal"
;zpm "install objectscript-openapi-definition"
;zpm "install iris-key-uploader"
quit


;ZN "%SYS"
;WRITE "Import Web applications last" 
;SET tSC = ##class(Security.Applications).Import("$ClassImportDir"_"/Application.xml")
;zw tSC
;WRITE:(tSC'=1) "[ FAIL ] Import Web applications configuration"
;DO:(tSC'=1) \$SYSTEM.Process.Terminate(,1),h
;WRITE "[ OK ] Import Web applications configuration"

;ZN "USER"

;WRITE "Back in objectscript mode"


;SET tSc = \$SYSTEM.OBJ.ImportDir("$ClassImportDir", "Installer.cls", "cubk", .tErrors, 1)
;WRITE:(tSc'=1) "[ FAIL ] Import and compile the installer class: "_tErrors
;DO:(tSc'=1) \$SYSTEM.Process.Terminate(,1),h
;WRITE "[ OK ] Import and compile the installer class"


WRITE "[ OK ] Everything is OK."
halt
EOF
