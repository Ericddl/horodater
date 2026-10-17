#!/bin/sh

dateDuJour=$(date +%Y%m%d)


for i in "$@"
do
	chemin=$(dirname "$i")
	fichier=$(basename "$i")
	mv "$i" "$chemin"/"$dateDuJour""_""$fichier" &
done
