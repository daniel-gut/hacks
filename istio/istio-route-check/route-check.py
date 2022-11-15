#!/usr/bin/env python3

import subprocess
import json
import re
import argparse
import fnmatch
from urllib.parse import urlparse



vshttp = {   'hostname_match': None,
                'rulename': None,
                'http': []
            }

def get_virtual_services(context):

    command = "kubectl get vs -A -ojson"

    if context == None:
        vsraw = subprocess.run([command], shell=True, capture_output=True)
    else:
        context = " --context " + str(context)
        command = command + context
        vsraw = subprocess.run([command], shell=True, capture_output=True)

    vs = json.loads(vsraw.stdout)

    return vs

def get_target(url):

    if not urlparse(url).scheme:
        url = "http://"+url

    return urlparse(url)

def get_empty_vsmatch():
    vsmatch = { 'match': {
                'uri': {
                    'type': None,
                    'expression': None,
                },
                'authority': {
                    'type': None,
                    'expression': None
                },
            },
            'rewrite': {
                'enabled': None,
                'authority': None,
                'uri': None
            },
            'redirect': {
                'enabled': None,
                'authority': None,
                'uri': None
            },
            'route': {
                'enabled': None,
                'host': None,
                'port': None
            },
            'defaultroute': {
                'enabled': None,
                'host': None,
                'port': None
            },
            }
    return vsmatch

def search_match(vs, t):

    global vshttp

    if t.path == "":
        path = "/"  # If path is "" results seem to be wrong. It might be that istio adds a trailing / if path is empty
    else:
        path = t.path

    for items in vs["items"]:
        for attribute in items["spec"]:
            if attribute == "hosts":
                for host in items["spec"][attribute]:
                    if hostname_in_vs(host, t.hostname):
                        vshttp["hostname_match"] = host
                        for attribute in items["spec"]:
                            if attribute == "http":
                                for http in items["spec"]["http"]:
                                    vshttp = get_http_match(vshttp, http, path, t.hostname, str(items["metadata"]["name"]))
                                if len(vshttp["http"]) >0:
                                    for existingvsmatch in vshttp["http"]:
                                        vsmatch = existingvsmatch
                                else:
                                    vsmatch = get_empty_vsmatch()
                                if  ( vsmatch["rewrite"]["enabled"] != True ) and ( vsmatch["redirect"]["enabled"] != True ) and ( vsmatch["route"]["enabled"] != True ):
                                    if "route" in http:
                                        for route in http["route"]:
                                            vshttp["rulename"] = str(items["metadata"]["name"])
                                            vsmatch["defaultroute"]["enabled"] = True
                                            if "host" in route["destination"]:
                                                vsmatch["defaultroute"]["host"] = route["destination"]["host"]
                                            if "port" in route["destination"]:
                                                vsmatch["defaultroute"]["port"]  = str(route["destination"]["port"]["number"])
#                                             if len(vshttp["http"]) > 0:
#
#                                                 for http in vshttp["http"]:
#                                                     print(len(vshttp["http"]))
#                                                     vshttp["http"].append(vsmatch)
#                                             else:
#                                                 vshttp["http"].append(vsmatch)
                                            vshttp["http"].append(vsmatch)
                                else:
                                    vsmatch["defaultroute"]["enabled"] = False

    return vshttp

def hostname_in_vs(vshost, searchhost):

    if vshost.startswith("*"):
        if fnmatch.fnmatch(searchhost, vshost):
            return True
    elif searchhost == vshost:
        return True
    else:
        return False

def get_http_match(vshttp, http, path, hostname, rulename):

    if len(vshttp["http"]) >0:
        for existingvsmatch in vshttp["http"]:
            vsmatch = existingvsmatch
    else:
        vsmatch = get_empty_vsmatch()

    if "match" in http:
        for match in http["match"]:
            if match != None:
                if "uri" in match:
                    for k, v in match["uri"].items():
                        foundmatch = False
                        match k:
                            case "prefix":
                                if (path.startswith(v)) and (v != vsmatch["match"]["uri"]["expression"]):
                                    vsmatch["match"]["uri"]["type"] = "prefix"
                                    foundmatch = True
                            case "exact":
                                if (v == path) and (v != vsmatch["match"]["uri"]["expression"]):
                                    vsmatch["match"]["uri"]["type"] = "exact"
                                    foundmatch = True
                            case "regex":
                                rematch = re.fullmatch(v, path)
                                if (rematch) and (v != vsmatch["match"]["uri"]["expression"]):
                                    vsmatch["match"]["uri"]["type"] = "regex"
                                    foundmatch = True
                        if foundmatch:
                            vshttp["rulename"] = rulename
                            vsmatch["match"]["uri"]["expression"] = v

                            if "route" in http:
                                for route in http["route"]:
                                    if "host" in route["destination"]:
                                        vsmatch["route"]["host"] = route["destination"]["host"]
                                        vsmatch["route"]["enabled"] = True
                                    if "port" in route["destination"]:
                                        vsmatch["route"]["port"] = str(route["destination"]["port"]["number"])
                                        vsmatch["route"]["enabled"] = True

                            if "rewrite" in http:
                                for rewrite in http["rewrite"]:
                                    if "uri" in rewrite:
                                        vsmatch["rewrite"]["uri"] = http["rewrite"]["uri"]
                                        vsmatch["rewrite"]["enabled"] = True
                                    if "authority" in rewrite:
                                        vsmatch["rewrite"]["authority"] = http["rewrite"]["authority"]
                                        vsmatch["rewrite"]["enabled"] = True

                            if "redirect" in http:
                                for redirect in http["redirect"]:
                                    if "uri" in redirect:
                                        vsmatch["redirect"]["uri"] = http["redirect"]["uri"]
                                        vsmatch["redirect"]["enabled"] = True
                                    if "authority" in redirect:
                                        vsmatch["redirect"]["authority"] = http["redirect"]["authority"]
                                        vsmatch["redirect"]["enabled"] = True
                            vshttp["http"].append(vsmatch)

                if match != None:
                    if "authority" in match:
                        for k, v in match["authority"].items():
                            foundmatch = False
                            match k:
                                case "prefix":
                                    if (hostname.startswith(v)) and (v != vsmatch["match"]["authority"]["expression"]):
                                        vsmatch["match"]["authority"]["type"] = "prefix"
                                        foundmatch = True
                                case "exact":
                                    if (v == hostname) and (v != vsmatch["match"]["authority"]["expression"]):
                                        vsmatch["match"]["authority"]["type"] = "exact"
                                        foundmatch = True
                                case "regex":
                                    rematch = re.fullmatch(v, hostname)
                                    if (rematch) and (v != vsmatch["match"]["authority"]["expression"]):
                                        vsmatch["match"]["authority"]["type"] = "regex"
                                        foundmatch = True

                            if foundmatch:
                                vshttp["rulename"] = rulename
                                vsmatch["match"]["authority"]["expression"] = v

                                if "route" in http:
                                    for route in http["route"]:
                                        if "host" in route["destination"]:
                                            vsmatch["route"]["host"] = route["destination"]["host"]
                                            vsmatch["route"]["enabled"] = True
                                        if "port" in route["destination"]:
                                            vsmatch["route"]["port"] = str(route["destination"]["port"]["number"])
                                            vsmatch["route"]["enabled"] = True

                                if "rewrite" in http:
                                    for rewrite in http["rewrite"]:
                                        if "uri" in rewrite:
                                            vsmatch["rewrite"]["uri"] = rewrite["uri"]
                                            vsmatch["rewrite"]["enabled"] = True
                                        if "authority" in rewrite:
                                            vsmatch["rewrite"]["authority"] = rewrite["authority"]
                                            vsmatch["rewrite"]["enabled"] = True

                                if "redirect" in http:
                                    for redirect in http["redirect"]:
                                        if "uri" in redirect:
                                            vsmatch["redirect"]["uri"] = redirect["uri"]
                                            vsmatch["redirect"]["enabled"] = True
                                        if "authority" in redirect:
                                            vsmatch["redirect"]["authority"] = redirect["authority"]
                                            vsmatch["redirect"]["enabled"] = True

                                    vshttp["http"].append(vsmatch)

    return vshttp

def print_results(results, t):

    if results["hostname_match"]:
        print("--- Request Actions ---")
        for h in  results["http"]:
            for kind in h:
                match kind:
                    case "rewrite":
                        if h[kind]["enabled"]:
                            if h[kind]["authority"] != None:
                                target = h[kind]["authority"]
                            else:
                                target = t.hostname
                            if h[kind]["uri"] != None:
                                target = target + h[kind]["uri"]
                            print("Rewrite request to: " + target)
                    case "redirect":
                        if h[kind]["enabled"]:
                            if h[kind]["authority"] != None:
                                target = h[kind]["authority"]
                            else:
                                target = t.hostname
                            if h[kind]["uri"] != None:
                                target = target + h[kind]["uri"]
                            print("Redirect to: " + target)
                    case "route":
                        if h[kind]["enabled"]:
                            if h[kind]["host"] != None:
                                targetservice = h[kind]["host"]
                                target = targetservice
                            if h[kind]["port"] != None:
                                targetport = h[kind]["port"]
                                target = targetservice+":"+targetport
                            print("Sending request to: " + target)
                    case "defaultroute":
                        #print(h["defaultroute"])
                        if h[kind]["enabled"]:
                            if h[kind]["host"] != None:
                                host = h[kind]["host"]
                                defaultroute = host
                            if h[kind]["port"] != None:
                                port = h[kind]["port"]
                                defaultroute = host+":"+port
                            print("Using default route: " + defaultroute)


        # Printing some more rule details
        print("")
        print("--- Rule Details ---")
        print("Matching Hostname in Rule is: \"" + results["hostname_match"] +"\"")
        print("Defined in VirtualService Rule: \"" + vshttp["rulename"] +"\"")

        # Print Kind of match
        for h in results["http"]:
            for kind in h["match"]:
                if h["match"][kind]["type"] != None:
                    print("Match is based on: \"" + kind +"\"")
                    print("Match type is: \"" + h["match"][kind]["type"] +"\"")
                    print("Match expressions is: \"" + str(h["match"][kind]["expression"]) +"\"")


    else:
        print("No matching rule found for " + args.url + " in context " + args.context)

def main(url, context):

    vs = get_virtual_services(context)

    target = get_target(url)

    results = search_match(vs, target)

    print_results(results, target)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find istio route destination')
    parser.add_argument('--url', type=str, required=True, help='URL for which to find destination')
    parser.add_argument('--context', type=str, required=False, help='K8S cluster context of istio-rules (default: current context')
    args = parser.parse_args()

    main(args.url, args.context)
