import requests
from datetime import datetime
import functools
import io
import os
import sys
import stat

API_URL="https://api.modrinth.com/v2"
# API_URL="https://staging-api.modrinth.com/v2"

INFO="info"
VERS="versions"

HEADERS = {
    "User-Agent": "personal_use_mod_manager (mjball424@gmail.com)"
}
PARAMS = {
    "loaders": '["null"]',
    "game_versions": '["null"]'
}


BASH_START = """#!/usr/bin/env bash
set -euo pipefail

found=false

while IFS= read -r line; do
    if $found; then
        [[ -z "$line" || "$line" == \#* ]] && continue

        echo "Downloading from $line"
        curl -L -O "$line"
    fi

    [[ "$line" == "# Exit success" ]] && found=true

done < "$0"

exit 0

# Exit success
"""

WINDOWS_START = """@echo off
setlocal

set "found="

for /f "usebackq delims=" %%L in ("%~f0") do (
    if defined found (
        if not "%%L"=="" (
            echo Downloading from %%L
            curl -L -O "%%L"
            if errorlevel 1 (
                echo Failed: %%L
                exit /b 1
            )
        )
    )

    if "%%L"=="REM Exit success" (
        set found=1
    )
)

exit /b 0

REM Exit success
"""


def find_latest(mod:str):
    r = requests.get(
        API_URL + "/project/" + mod + "/version",
        headers=HEADERS,
        params=PARAMS
    )
    if r.status_code != 200:
        print("ERROR: Invalid status code")
        return None

    # Sort by version_type first (release->beta->alpha) then by release date
    def sort_condition(va, vb):
        if va["version_type"] != vb["version_type"]:
            if va["version_type"] == "release" or vb["version_type"] == "alpha":
                return -1
            else:
                return 1

        tstra = va["date_published"]
        ta = datetime.fromisoformat(tstra.replace("Z", "+00:00"))

        tstrb = vb["date_published"]
        tb = datetime.fromisoformat(tstrb.replace("Z", "+00:00"))

        if ta > tb:
            return -1
        elif ta < tb:
            return 1
        else:
            return 0

    vlist = r.json()
    if len(vlist) < 1:
        print(f"Warning: No versions of {mod} exist for {PARAMS["loaders"]}+{PARAMS["game_versions"]}")
        return None

    vlist = sorted(vlist, key=functools.cmp_to_key(sort_condition))

    return vlist[0]


DOWNLOAD_OPTIONAL = False
def recurse_dependencies(depends:list, download_list:dict):
    mod_cnt = 0

    # Separate list for downloads so we can more easily "bail" if dependencies are missing
    add_list = {}

    for d in depends:
        # Check if dependency is optional
        optional = True if d["dependency_type"] != "required" else False
        if optional and not DOWNLOAD_OPTIONAL:
            continue

        # Get latest version (if any)
        vd = find_latest(d["project_id"])
        if vd is None:
            if vd is optional: continue
            else: return None # Return "failure" if required dependency is missing

        # Skip if mod already in download_list
        prid = vd["project_id"]
        if prid in download_list.keys(): continue

        # Add to secondary list and increment mod count
        add_list[prid] = vd
        mod_cnt += 1
    
    # Merge download lists
    for key,val in add_list.items():
        download_list[key] = val

    return mod_cnt


def create_download_list(requested:list):
    download_list = {}

    req_mod_cnt = 0
    dep_mod_cnt = 0

    for r in requested:
        print(f"Finding {r}...")

        # Get latest version of requested mod (if any)
        vr = find_latest(r)
        if vr is None:
            continue

        # Check if requested mod already in download_list
        # Should only happen if user mistakenly listed a mod multiple times or listed dependencies
        prid = vr["project_id"]
        if prid in download_list:
            print("Requested mod " + r + " already in download list")
            continue

        # Handle dependencies
        if "dependencies" in vr:
            ret = recurse_dependencies(vr["dependencies"], download_list)
            # Skip if dependencies are missing
            if ret is None:
                print(f"ERROR: Missing dependencies for {r}, skipping")
                continue
            # Otherwise increment dependency count and keep going
            dep_mod_cnt += ret
            if ret > 0: print(f"    Found {ret} dependencies")
        
        # Add to download_list and increment count
        download_list[prid] = vr
        req_mod_cnt += 1
    
    print(f"{req_mod_cnt+dep_mod_cnt} mods will be downloaded ({req_mod_cnt} requseted with {dep_mod_cnt} dependencies)")

    return download_list

script_urls = None
script_sh = None
script_bat = None
def prepare_scripts(output_dir):
    global script_urls, script_sh, script_bat

    script_dir = output_dir + "/scripts"
    if not os.path.exists(script_dir): os.makedirs(script_dir)

    script_urls = open(script_dir + "/mods.txt", "w")
    script_sh = open(script_dir + "/mods.sh", "w")
    script_bat = open(script_dir + "/mods.bat", "w")

    script_sh.write(BASH_START)
    script_bat.write(WINDOWS_START)


def close_scripts():
    global script_urls, script_sh, script_bat

    shpath = script_sh.name
    shstat = os.stat(script_sh.name)

    script_urls.close()
    script_sh.close()
    script_bat.close()

    os.chmod(shpath, shstat.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    

def add_url_to_scripts(url):
    global script_urls, script_sh, script_bat

    script_urls.write(url + "\n")
    script_sh.write(url + "\n")
    script_bat.write(url + "\n")
    pass


# Source - https://stackoverflow.com/a/16696317
# Posted by Roman Podlinov, modified by community. See post 'Timeline' for change history
# Retrieved 2026-07-18, License - CC BY-SA 4.0
def download_file(url, filepath):
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk: 
                f.write(chunk)


def download_all(download_list:list, output_dir):
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    if output_dir[-1] not in "/\\": output_dir += "/"

    prepare_scripts(output_dir)

    for d in download_list:
        for f in d["files"]:
            filepath = output_dir + f["filename"]
            url = f["url"]

            if os.path.exists(filepath):
                print(f"Warning: file \"{filepath}\" already exists")
                continue

            # Skip non-jar files just in case
            if url[-4:] != ".jar": continue
                
            # download_file(url, filepath)
            print(f"DOWNLOAD {url}")
            add_url_to_scripts(url)

            break # Only going to do the first file, not sure what the other files are for
    
    close_scripts()


def parse_csv(filepath):
    # Open csv file
    file = open(filepath, "r")
    
    # [ (mod-slug-or-id:str, required:boolean, comment:str)... ]
    modlist = []

    for line in file:
        # Ignore comments
        if line[0] == '#': continue

        # Split on commas
        items = line.split(sep=",", maxsplit=2)
        if len(items) < 1:
            continue

        # Get mod, skip if mod is empty
        mod = items[0].strip()
        if len(mod) < 1:
            continue

        # Get required state and commment, default to True and empty
        req = False if len(items) > 1 and items[1].strip().lower()[0] == "n" else True
        comment = "" if len(items) < 3 else items[2].strip()

        # Apppend to modlist
        modlist.append((mod, req, comment))

    # Done with csv file
    file.close()

    # Print all mods
    print("ID/SLUG                  | Req | Comments")
    for info in modlist:
        print(f"{info[0]:24} | {"Yes" if info[1] else "No "} | {info[2]}")

    final_list = []
    all_response = None

    # Prompt user to select optional mods
    print("\nSELECT OPTIONAL MODS")
    for info in modlist:
        # Always add required mods to final modlist
        if info[1]: 
            final_list.append(info[0])
            continue
        
        # If the user entered yall/nall, use y/n as answer for all remaining prompts
        if all_response is not None:
            if all_response:
                final_list.append(info[0])
            continue

        while(True):
            # Display mod and ask user if they want to download
            print(f"{info[0]:24} | {"Yes" if info[1] else "No "} | {info[2]}")
            r = input("Use this mod? [y/n]: ")
            r = r.strip().lower()[0:4]

            # Check for yall/nall response
            if r == "yall": all_response = True
            elif r == "nall": all_response = False
            r = r[0]

            # Check for y/n response
            if r == "y":
                final_list.append(info[0])
                break
            elif r == "n":
                break
    
    return final_list



def main():
    global PARAMS

    if len(sys.argv) < 4 or len(sys.argv) > 5:
        print("Usage: python script.py [mods.csv] [output_dir] [game_version] [optional:loader, default=fabric]")
        exit(1)
    
    mod_list_file = sys.argv[1]
    output_dir = sys.argv[2]
    game_version = sys.argv[3].strip()
    loader = "fabric" if len(sys.argv) < 5 else sys.argv[4].strip()

    # Set query parameters
    PARAMS["game_versions"] = '["' + game_version + '"]'
    PARAMS["loaders"] = '["' + loader + '"]'

    if not os.path.exists(output_dir): os.makedirs(output_dir)

    # Parse list and confirm what mods the user wants
    confimred_list = parse_csv(mod_list_file)

    # Get download list
    download_dict = create_download_list(confimred_list)
    download_list = download_dict.values()
        
    # Download all mods
    download_all(download_list, output_dir)

    print("\nDownloads complete")

    pass

if __name__ == "__main__":
    main()