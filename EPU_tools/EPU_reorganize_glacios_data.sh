#!/usr/bin/env bash

# Cmds to reorganize an EPU session 

## check if directories exist 

## create the directories that dont exist 
mkdir {xml,jpg,movies,mrc}

for m in $(find Images-Disc1/ -name *Fractions.mrc); do ln -s ../$m movies/; done

for m in $(find Images-Disc1/ -name *Data*.mrc ! -name *Fractions.mrc); do ln -s ../$m mrc/; done

for m in $(find Images-Disc1/ -name *Data*.xml ! -name *Fractions.xml); do ln -s ../$m xml/; done

