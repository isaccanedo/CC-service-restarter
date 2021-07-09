#! /opt/zenoss/bin/python
import json
import logging
import sys
import os
# uncomment the below when deploying on mon
#sys.path.append('/serviced')
import requests

# initialise logger.  In order, it creates a Logger instance, then a FileHandler and a Formatter.
# It attaches the Formatter to the FileHandler, then the FileHandler to the Logger.
# Finally, it sets a debug level for the logger.
logger = logging.getLogger('output')
handler = logging.FileHandler('service_restart.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# CC rest api creds, FILL IN
login = {
    "Username": "",
    "Password": ""
}

# server details, FILL IN
server_ip = ""
port = ""

# list of services by ID, FILL IN
# examples, CentralQuery, Zenoss.resmgr
servicelist = ["", ""]

# get cookies for api authorisation
def getCookies():
    # log into control center and get cookie and store it for further requests.
    try:
        r = requests.post('https://{}:{}/login'.format(server_ip, port), json=login, verify=False, headers={"Host": "localhost"})
    except requests.exceptions.ProxyError:
        logger.error("There is a proxy issue, the proxy server may not be able to contact {}...".format(server_ip))
        logger.info("No services have been restarted.")
        logger.info("----Failed-----")
        sys.exit(1)

    if r.status_code != 200:
        logger.error("Unable to retrieve cookie session for authentication against CC-API...")
        logger.error(r.text)
        sys.exit(1)

    logger.info("Cookies retrieved.")

    return r.cookies

# this method finds the service information for in question. Acts as a gateway to searchAllServices
def findServices(cookie, *args):
    listOfServ = args
    # error checking
    if type(listOfServ) != tuple:
        logger.error("Please make sure you are passing a list of strings")
    for i in listOfServ[0]:
        if type(i) != str:
            logger.error("There is a non-string value on the list")

    req = requests.get('https://{}:{}/servicestatus'.format(server_ip, port),
                       headers={"Host": "localhost", "Content-type": "application/json"}, verify=False,
                       cookies=cookie)
    servicesjson = json.loads(req.text)
    service_meta = {}

    for each in listOfServ[0]:
        for e in servicesjson:
            if e['Name'] == each:
                locald = {}
                locald['DockerName'] = e['ID']
                locald['Host'] = e['HostID']
                locald['ServiceID'] = e['ServiceID']
                service_meta[each] = locald

    return service_meta


def main():
    logger.info("----Starting Script-----")
    logger.info("Getting cookies...")
    login_cookies = getCookies()

    logger.info("Getting metadata for services...")
    metadata = findServices(login_cookies, servicelist)

    for k ,v in metadata.iteritems():
        if k == "Zenoss.resmgr":
            # make request to restart zproxy
            restart_zproxy = requests.delete('https://{}:{}/hosts/{}/{}'.format(server_ip, port, v['Host'], v['DockerName']),
                                     headers={"Host": "localhost", "Content-type": "application/json"}, verify=False,
                                     cookies=login_cookies)
            logger.info("Successfully retrieved for Zenoss.resmgr, metadata - Host: {}, Dockername: {}".format(v['Host'], v['DockerName']))
        else:
            # make the request to control centre to restart the Central query service
            r = requests.put('https://{}:{}/services/{}/restartService'.format(server_ip, port, v['ServiceID']),
                             headers={"Host": "localhost", "Content-type": "application/json"}, json={"": ""},
                             verify=False, cookies=login_cookies)
            logger.info("Successfully retrieved for {}, metadata - Host: {}, Dockername: {}".format(k, v['Host'], v[
                'DockerName']))

    logger.info("Successfully restarted all services...")
    logger.info("----End of Script-----")

if __name__ == "__main__":
    main()
