#!/bin/bash

# Config 
ORGANIZATION=example-company
GITHUB_TOKEN=dummy-token
MAX_ITEMS=100
CURRENT_PAGE=1

# Get number of pages using header information of API response
NUMBER_OF_PAGES=$(curl -sI https://$GITHUB_TOKEN:@api.github.com/orgs/$ORGANIZATION/repos?per_page=$MAX_ITEMS | grep -oP '\d+(?=>; rel\=\"last\")')

# Going trough all repopsitories and cloning it to current folder
while [ $CURRENT_PAGE -le $NUMBER_OF_PAGES ]
do
    curl -s https://$GITHUB_TOKEN:@api.github.com/orgs/$ORGANIZATION/repos?per_page=$MAX_ITEMS\&page=$CURRENT_PAGE | jq .[].ssh_url | xargs -n 1 git clone
    CURRENT_PAGE=$(( $CURRENT_PAGE +1 ))
done

