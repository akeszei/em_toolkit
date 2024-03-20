#!/usr/bin/env bash 

## Point to file with IP addresses and associated comment in the format:
# x.x.x.x comment
# y.y.y.y comment_2
# ...

FILE='ip_table.txt'


## Sanity check the script is run with root priviledge
if ! [ $(id -u) = 0 ]; then
    echo " !! ERROR !! Script must be run with elevated priviledges (add sudo)"
    exit 1
fi

## Clear existing rules (option is given to the user y/n) 
ufw reset

## Parse the file line-by-line, adding each suitable entry as a firewall rule 
cat $FILE | while read line
do
    ## filter the line into an array based on space delimitation
    read -a ip_entry <<< "$line"

    ## sanity check the array length is 2, otherwise print a warning and skip the entry
    if [ "${#ip_entry[@]}" -ne 2 ]; then
        echo " !! WARNING !! Entry found, but more than 2 columns were detected:"
        echo "       entry >>> $line"
    else

        ## for readability, rename the array entries based on their expected value types 
        ip_addr=${ip_entry[0]}
        comment=${ip_entry[1]}
        ## run the assignment protocol for each ip address to the firewall 
        #echo "CMD =" ufw allow proto tcp from $ip_addr to any port 22,39000 comment \'$comment\'
        ufw allow proto tcp from $ip_addr to any port 22,39000 comment "$comment"
        #echo " Parsed entry:   $ip_addr   $comment"
    fi
done

## Enable the firewall and print the resulting settings 
echo " Firewall rules updated: "
ufw enable 
ufw status 

