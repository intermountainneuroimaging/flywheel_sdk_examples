#!/bin/bash
export FLYWHEEL_CLI_BETA=true
input_file="disable.txt"
while IFS= read -r gear_id
do
   echo "disabling $gear_id"
   fw admin gears disable "$gear_id"
   echo "   finished disabling $gear_id"
done < "$input_file"