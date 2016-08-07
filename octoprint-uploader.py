#!/usr/bin/python

import requests
import hashlib
import os
import yaml
import sys
import time

def get_local_files(dir):
	local_files = {}
	for local_file in os.listdir(dir):
		if local_file.endswith(".gcode") == False:
			continue

		hasher = hashlib.sha1()
		with open(dir + local_file, 'rb') as file_handle:
    			file_buf = file_handle.read()
    			hasher.update(file_buf)

		local_files[local_file] = hasher.hexdigest()
	return local_files

def get_remote_files(host, key):
	remote_files = {}

	api_headers = {'X-Api-Key': key}
	api_result = requests.get("http://" + host + "/api/files", headers = api_headers);
	if api_result.status_code != 200:
		return {}


	api_json = api_result.json()
	for remote_file in api_json["files"]:
		remote_files[remote_file["name"]] = remote_file["hash"]

	return remote_files

def delete_remote_file(host, key, name):
	api_headers = {'X-Api-Key': key}
	api_result = requests.delete("http://" + host + "/api/files/local/" + name, headers = api_headers);
	return (api_result.status_code == 204)

def upload_local_file(host, key, name):
	api_headers = {'X-Api-Key': key}
	api_files = {"file": (os.path.basename(name), open(name, "rb")), "select": "true"}
	api_result = requests.post("http://" + host + "/api/files/local", headers = api_headers, files = api_files) 
	return (api_result.status_code == 201)


# check arguments
if len(sys.argv) <= 1:
	print "Usage: " + sys.argv[0] + " config.yaml.."
	print "  config.yaml  One or more configuration files"
	sys.exit()

for conf_file in sys.argv[1:]:
	# load configuration
	conf_dict = yaml.safe_load(open(conf_file))
	
	conf_directory = conf_dict["directory"]
	conf_host = conf_dict["host"]
	conf_apikey = conf_dict["apikey"]
	conf_limit = conf_dict["limit"]	

	# create list of local and remote files
	local_files = get_local_files(conf_directory)
	remote_files = get_remote_files(conf_host, conf_apikey)

	# walk through local files and upload if necessary
	for file_name, local_hash in local_files.items():
		if file_name in remote_files:
			remote_hash = remote_files[file_name]
		else:
			remote_hash = ""
		
		full_name = conf_directory + file_name
		upload_file = False
		if os.path.getmtime(full_name) < time.time() - conf_limit:
			print "[Old] " + file_name + " =>",
		else: 
			if remote_hash == "":
				print "[New] " + file_name + " =>",
				upload_file = True
			else:
				if local_hash == remote_hash:
					print "[Unchanged] " + file_name + " =>",
				else:
					print "[Changed] " + file_name + " =>",	
					if delete_remote_file(conf_host, conf_apikey, file_name):
						upload_file = True
					else:
						print "DELETE FAILED"
	
		if upload_file == True:
			if upload_local_file(conf_host, conf_apikey, full_name):
				print "OK"
			else:
				print "UPLOAD FAILED"
		else:
			print "OK"


