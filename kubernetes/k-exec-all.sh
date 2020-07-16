#! /bin/bash

FILENAME="user-ids-prod.txt"
COMMAND=id
EXCLUDED_NAMESPACES=(istio-system kube-system)
EXCLUDED_CONTAINERS="istio-proxy\|cloudsql-proxy"

echo "#############################" | tee -a $FILENAME
echo "Excluded namespaces $EXCLUDED_NAMESPACES" | tee -a $FILENAME
echo "Excluded container $EXCLUDED_CONTAINERS" | tee -a $FILENAME
echo "#############################" | tee -a $FILENAME

# Get all namespaces
for namespace in $(kubectl get ns --no-headers | awk {' print $1 }');
    do
    # if namespaces is excluded, only report deployments and statefulsets, don't run commands
    if [[ ! " ${EXCLUDED_NAMESPACES[@]} " =~ " ${namespace} " ]]; then

        # Get all Deployments in all namespaces except excluded namespaces
        for deployment in $(kubectl get deployments -n $namespace  --no-headers 2> /dev/null | awk {' print $1 }')
            do

            echo "-----------------------------" | tee -a $FILENAME
            echo "$deployment in namespace $namespace" | tee -a $FILENAME
            # Get 1 running pod for every deployment
            pod=$(kubectl get pods -n $namespace --no-headers | grep $deployment | head -n1 | awk '{print $1}')

            # get container
            container=$(kubectl get pods -n $namespace $pod -ojson | jq -r .spec.containers[].name | grep -v $EXCLUDED_CONTAINERS)

            # Run command for every pod
            result=$(kubectl exec -it -n $namespace $pod -c $container -- $COMMAND)

            echo "$result" | tee -a $FILENAME

        done


        # Get all Statefulsets in all namespaces
        for statefulset in $(kubectl get statefulsets -n $namespace  --no-headers 2> /dev/null | awk {' print $1 }')
            do

            echo "-----------------------------" | tee -a $FILENAME
            echo "$statefulset in namespace $namespace" | tee -a $FILENAME
            # Get 1 running pod for every deployment
            pod=$(kubectl get pods -n $namespace --no-headers | grep $statefulset | head -n1 | awk '{print $1}')

            # get container
            container=$(kubectl get pods -n $namespace $pod -ojson | jq -r .spec.containers[].name | grep -v $EXCLUDED_CONTAINERS)

            # Run command for every pod
            result=$(kubectl exec -it -n $namespace $pod -c $container -- $COMMAND)

            echo "$result" | tee -a $FILENAME

        done
    fi

done