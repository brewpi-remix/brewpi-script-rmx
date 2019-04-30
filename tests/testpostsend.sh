#!/bin/bash

data='{"mdns_id":"tiltbridge","tilts":{"Purple":{"color":"Purple","gravity":"1.088","gsheets_name":"","temp":70}}}'
url='http://brewpi.local/testpostrec.php'
curl -d "$data" -H "Content-Type: application/json" -X POST "$url"
echo 
