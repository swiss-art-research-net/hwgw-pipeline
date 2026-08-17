import base64
import requests
import hashlib
import json
import re
import os
import sys
from urllib.request import urlopen
from datetime import datetime, timezone


def _load_metadata(path):
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def _write_metadata(path, metadata):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=4)


def _update_metadata_for_download(localfile):
    folder = os.path.dirname(localfile)
    filename = os.path.basename(localfile)
    metadata_path = os.path.join(folder, 'metadata.json')

    metadata = _load_metadata(metadata_path)
    files = metadata.setdefault('files', {})
    file_metadata = files.setdefault(filename, {})

    now_utc = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    file_metadata['lastDownloaded'] = now_utc
    metadata['lastDownloaded'] = now_utc

    _write_metadata(metadata_path, metadata)

# Call with arguments:
# 1: GitHub username
# 2: GitHub personal access token
# 3: Repository
# 4: path to file
if len(sys.argv) < 6:
    sys.stderr.write("Insufficient arguments\n")
    exit()

username = sys.argv[1]
token = sys.argv[2]
repo = sys.argv[3]
path = sys.argv[4]
localfile = sys.argv[5]
branch = sys.argv[6] if len(sys.argv) > 6 else "main"

folder = path.rsplit('/',1)[0]
file = path.rsplit('/',1)[1]

folderURL = f'https://api.github.com/repos/{repo}/contents/{folder}?ref={branch}'
folderRequest = requests.get(folderURL, auth=(username, token))
folderData = folderRequest.json()

try:
    requestedFile = [d for d in folderData if d['name'] == file][0]
except:
    sys.stderr.write("could not find file %s in path %s\n" % (file, folderURL))
    exit()

# Check if file already exists locally and if size matches
if os.path.exists(localfile):
    with open(localfile, 'rb') as f:
        localSize = os.path.getsize(localfile)
    if requestedFile['size'] == localSize:
        sys.stderr.write("File already exists locally and file size matches\n")
        exit()

fileURL = 'https://api.github.com/repos/' + repo + '/git/blobs/' + requestedFile['sha']
fileRequest = requests.get(fileURL, auth=(username, token))

result = base64.b64decode( fileRequest.json()['content'] ).decode('UTF-8', 'ignore')
if not "https://git-lfs.github.com/spec/v1" in result:
    with open(localfile, 'w', encoding='utf-8') as f:
        f.write(result)
    _update_metadata_for_download(localfile)
else:
    # Download from GIT LFS
    sha = re.findall(r'sha256:([a-z0-9]*)', result)[0]
    size = int(re.findall(r'size ([0-9]*)', result)[0])

    # Check if file already exists locally and if SHA and Size match
    if os.path.exists(localfile):
        with open(localfile, 'rb') as f:
            localSHA = hashlib.sha256(f.read()).hexdigest()
            localSize = os.path.getsize(localfile)
        if sha == localSHA and size == localSize:
            sys.stderr.write("File already exists locally and is up to date\n")
            exit()

    url =  "https://github.com/" + repo + ".git/info/lfs/objects/batch"
    data = {
        'operation': 'download', 
        'transfer': ['basic'], 
        'objects': [
            {'oid': sha, 'size': size}
        ]}
    headers = {'Content-type': 'application/json', 'Accept': 'application/vnd.git-lfs+json'}

    r = requests.post(url, data=json.dumps(data), headers=headers, auth=(username, token))
    downloadurl = r.json()['objects'][0]['actions']['download']['href']

    response = requests.get(downloadurl)

    with open(localfile, 'w', encoding='utf-8') as f:
        f.write(response.content.decode('UTF-8', 'ignore'))
    _update_metadata_for_download(localfile)

sys.stderr.write("Done!\n")