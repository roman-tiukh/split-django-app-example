#!/bin/bash

poetry export -f requirements.txt --without-hashes | sed 's/;.*//' > requirements.txt
