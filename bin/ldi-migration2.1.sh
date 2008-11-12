#!/bin/sh

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
	echo "Usage: $0 [debinstallrc_file]"
	echo "By default /etc/debinstall/debinstallrc will be used."
	exit
fi

echo "[Run migration script to ldi 2.1]"

if [[ "x$(id -un)" != "xroot" ]]; then
	echo "ERROR: You need to be ROOT" >&2
	exit 1
fi

DEBINSTALLRC=${1:-/etc/debinstall/debinstallrc}
if [[ ! -f "$DEBINSTALLRC" ]]; then
	echo "ERROR: '$DEBINSTALLRC' is not a valid file" >&2
	exit 1
fi

echo "* retrieve debinstallrc file: $DEBINSTALLRC"

CONFIG_DIR=$(grep '^configurations=' $DEBINSTALLRC | cut -d'=' -f2)
DEST_DIR=$(grep '^destination=' $DEBINSTALLRC | cut -d'=' -f2)

if [[ ! -d "$CONFIG_DIR" ]]; then
	echo "ERROR: cannot retrieve configuration directory ($CONFIG_DIR)" >&2
	exit 1
elif [[ ! -d "$DEST_DIR" ]]; then
	echo "ERROR: cannot retrieve destination directory ($DEST_DIR)" >&2
	exit 1
else
	echo "* retrieve configuration directory: $CONFIG_DIR"
	echo "* retrieve destination directory: $DEST_DIR"
	echo "* go to destination directory: $DEST_DIR"
	cd $DEST_DIR
	echo "* entering in each directory now..."
	for i in *; do
		if [[ -d "$i/debian" && ! -h "$i/debian" ]]; then
			echo "** processing $i"
			echo "*** rename debian/ to dists/"
			mv $i/debian $i/dists
			echo "*** add a symlink from 'debian/' to 'dists/'"
			ln -s dists $i/debian
			echo "*** retrieve current distrib"
			DISTRIB=$(ls -1 $i/dists | head -n1)
			if [[ ! -d "$i/dists/$DISTRIB" ]]; then
				echo "ERROR: cannot retrieve current distribution ($DISTRIB)" >&2
				exit 1
			fi
			echo "*** move incoming queue to incoming/$DISTRIB"
			mv -f $i/incoming $i/$DISTRIB
			mkdir $i/incoming
			mv $i/$DISTRIB $i/incoming/
			ls -l $i
		else
			echo "WARNING:'$i' is not a valid directory"
		fi
	done;
	echo "* correct user ownership (use debinstall user)"
	chown -R debinstall:debinstall $DEST_DIR
	echo "* correct directories permissions (0775)"
	find $DEST_DIR -type d -execdir chmod 0755 {} \;
	echo "* correct files permissions (0664)"
	find $DEST_DIR -type f -exec chmod 0664 {} \;
	echo "* rename ArchiveDir value in configuration files (old config files will be renamed to .migr21)"
	sed -i'.migr21' 's/ArchiveDir "debian"/ArchiveDir "dists"/' $CONFIG_DIR/*-apt.conf
fi
echo "Migration done."
