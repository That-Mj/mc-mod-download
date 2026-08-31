import requests
from datetime import datetime
import functools
import io
import os
import sys
import stat
import argparse

### GLOBALLY SET PARAMETERS

# find_latest()
API_URL="https://api.modrinth.com/v2"
HEADERS = {
    "User-Agent": "personal_use_mod_manager"
}
PARAMS = {
    "loaders": '["null"]',
    "game_versions": '["null"]'
}

# recurse_dependencies
INC_OPTIONAL = True

# get_all_mod_info
REQUIRED_OVERRIDE = None

### END GLOBALLY SET PARAMETERS


# Sanitize a string to replace ';', which is used as item seperators in lists/dicts in the script's data
# Note: ':' is also use to separate keys/values in dicts, but should be safe to use regardless
def sanitize(string:str):
    # https://www.w3schools.com/tags//ref_urlencode.asp
    string = string.replace(';', "%3B")
    # string = string.replace(':', '%3A')
    return string


# Creates a URL to the main page for the mod
def make_user_url(mod_id:str):
    return "https://modrinth.com/mod/" + mod_id


# Gets the download URL from a version dict/json
def get_url(version):
    for f in version["files"]:
        # Skip non-jar files just in case
        if f["filename"][-4:] != ".jar": continue
        return f["url"]
    return None


# Finds the latest version of the mod given the input parameters
def find_latest(mod:str):
    # Get response
    response = requests.get(
        API_URL + "/project/" + mod + "/version",
        headers=HEADERS,
        params=PARAMS
    )
    # Error check, otherwise proceed to grab list of available versions
    if response.status_code != 200:
        print("ERROR: Invalid status code")
        return None
    version_list = response.json()

    # If no versions available, display warning and provide URL to mod page
    if len(version_list) < 1:
        print(f"Warning: No versions of {mod} exist for {PARAMS["loaders"]}+{PARAMS["game_versions"]}")
        print(f"  {make_user_url(mod)}")
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

    # Get sorted list
    version_list = sorted(version_list, key=functools.cmp_to_key(sort_condition))

    # Return first mod
    return version_list[0]


# Recursively finds all dependencies for the given mod `parent`
    # `history`: Dict: [project_id]: [version dict/json]
        # Record of all discovered version info. 
        # Used to avoid additional API calls, e.g. if the mod is a dependency 
        #  for a previous mod and therefore was already found. 
    # `found`: Dict: [project_id]: [download URL]
        # All found dependencies
    # `missing`: List: [project_id]
        # Required dependencies for which no valid version exists
    # return: Dict: [project_id]: [version dict/json], List: [project_id]
        # 1) Dictionary of all found dependencies
        # 2) List of all missing dependencies
def recurse_dependencies(parent, history, found=None, missing=None):
    # If no depencies, return empty list
    if not "dependencies" in parent: return {}, []

    # If none provided, initialize found and missing lists
    if found is None: found = { parent["project_id"]: get_url(parent) } # ID: URL
    if missing is None: missing = [] # ID

    for c in parent["dependencies"]:
        child_id = c["project_id"]

        # If this mod has already been checked, skip
        if child_id in found or child_id in missing:
            continue

        # Check if optional
        optional = False if c["dependency_type"] == "required" else True
        if not INC_OPTIONAL and optional: 
            continue

        # Get from history, otherwise regrab using api (find_latest(...))
        if child_id not in history:
            history[child_id] = find_latest(child_id)
        child_vers = history[child_id]

        # Get url, or set to None if no version available
        url = None
        if child_vers is not None:
            url = get_url(child_vers)
        
        # If url missing, either optional and we don't care, or add to missing
        if url is None:
            if optional:
                continue
            else:
                missing.append(child_id)
        # Url found, add to found
        else:
            found[child_id] = url
        
        recurse_dependencies(child_vers, history, found, missing)
    
    return found, missing


# Gets all mod info from the requested list
    # Requested: 
def get_all_mod_info(requested:list):
    required = [] # List of ids/slugs
    optional = {} # ID: (name, desc)
    dependencies = {} # ID: [Dep1, Dep2, ...]
    urls = {} # ID: Url, all mods MUST be in here

    history = {} # ID: Version, all mods MUST be in here

    for mod_id, mod_req, mod_comm in requested:
        # Skip or force-include optional mods
        if REQUIRED_OVERRIDE is not None and not mod_req:
            if REQUIRED_OVERRIDE:
                mod_req = True
            else:
                continue
        print(f"Finding {mod_id}...")

        # Get latest version of requested mod (if any)
        if mod_id not in history:
            history[mod_id] = find_latest(mod_id)
        vers = history[mod_id]
        if vers is None:
            continue

        # Use project ID for identification
        prid = vers["project_id"]
        # Ensure history has a record for the project ID in case slug was used for mod_id
        if prid != mod_id:
            history[prid] = vers
        
        # Skip if mod is fully handled
        if prid in required:
            print("Requested mod " + mod_id + " already required")
            continue
        
        # If mod found in optional:
        if prid in optional:
            # If mod should be required
            if mod_req:
                # Add dependencies to the required list
                for dep_id in dependencies[prid]:
                    if dep_id in required: continue
                    required.append(dep_id)
                # Remove from optional and dependencies
                del optional[prid]
                del dependencies[prid]
                # Skip to next mod
                continue
            # If mod is supposed to be optional, then skip because it's where it's supposed to be already
            else:
                continue
            
        # Get URL
        url = get_url(vers)
        if url is None:
            print(f"Failed to get url for {mod_id}")
            continue

        # Get Dependencies
        mod_deps, missing = recurse_dependencies(vers, history)
        if len(missing) > 0:
            print("Missing the following dependencies: ")
            for m in missing:
                print(f"   {m} : {make_user_url(m)}")
            continue

        # MOD IS NOW VALID; MOD INFO CAN BE ADDED

        # Add URL (the only non-conditional mod info)
        urls[prid] = url

        # If mod is required
        if mod_req:
            required.append(prid)

            if len(mod_deps) > 0:
                # Add only new urls
                for id,url in mod_deps.items():
                    if id not in urls: urls[id] = url
                    if id not in required: required.append(id)
        
        # If mod is optional
        else:
            name = None

            # Get the title (or the closest thing available)
            if "title" in vers:
                name = vers["title"]
            else:
                r = requests.get(
                    API_URL + "/project/" + mod_id,
                    headers=HEADERS,
                    params=PARAMS
                ).json()

                if "title" in r:
                    name = r["title"]
                else:
                    name = mod_id

            # Replace any characters that might mess with
            name = sanitize(name)
            mod_comm = sanitize(mod_comm)

            optional[prid] = (name, mod_comm)

            if len(mod_deps) > 0:
                # Add all dependencies
                dependencies[prid] = list(mod_deps.keys())
                # Add only new urls
                for id,url in mod_deps.items():
                    if id in urls: continue
                    urls[id] = url
    
    # Just in case, delete any optional mods that are also required
    for r in required:
        # Delete from optionional
        if r in optional:
            del optional[r]
        
        # Delete all dependencies
        for id,deps in dependencies.items():
            if r in deps: deps.remove(r)
    
    dependencies = {id: deps for id,deps in dependencies.items() if len(deps) > 0}


    return required, optional, dependencies, urls


# Convers the required list to a string
def get_required_string(required:list):
    req_str = "\n# REQUIRED\n"

    for r in required:
        req_str += r + "\n"
    
    return req_str

# Converts the optional dict to a string
def get_optional_string(optional:dict):
    opt_str = "\n# OPTIONAL\n"

    for id, info in optional.items():
        line = id + ":" + info[0] + "," + info[1] + "\n"
        opt_str += line

    return opt_str

# Converts the depedencies dict to a string
def get_dependencies_string(dependencies:dict):
    dep_str = "\n# DEPENDENCIES\n"

    for id,deps in dependencies.items():
        line = id + ":"
        for d in deps:
            line += d + ","
        line = line[:-1] + "\n" # Strip trailing comma and replace with newline

        dep_str += line
    
    return dep_str

# Converts the URLs dict to a string
def get_urls_string(urls:dict):
    urls_str = "\n# URLS\n"

    for id,url in urls.items():
        line = id + ":" + url + "\n"
        urls_str += line
    
    return urls_str


# Convert all lists to strings, write to output files
def write_all(output_dir:str, required:list, optional:dict, dependencies:dict, urls:dict):
    total_str = "\n"

    use_simplified = len(optional) <= 0
    
    if not use_simplified:
        # Write advanced download script
        total_str = (
            get_required_string(required)
            + get_optional_string(optional)
            + get_dependencies_string(dependencies)
        )

    total_str += get_urls_string(urls)

    for filename, scripts in SCRIPTS.items():
        file = open(output_dir + "/" + filename, "w")
        script = scripts[1] if use_simplified else scripts[0]

        file.write(script)
        file.write(total_str)

        file.close()


def parse_csv(filepath):
    # Open csv file
    file = open(filepath, "r")
    
    # [ (mod-slug-or-id:str, required:boolean, comment:str)... ]
    modlist = []

    for line in file:
        # Ignore comments
        if line[0] == '#': continue

        line = line.strip()

        if len(line) < 1: continue

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
    
    return modlist


def main():
    global PARAMS, INC_OPTIONAL, REQUIRED_OVERRIDE

    parser = argparse.ArgumentParser(description="Modpack download script generator")
    parser.add_argument("-m", "--modpack", required=True, type=str, help=".csv file with each line of the following format: `[mod id/slug],[is required:y/n (OPTIONAL)],[any additional comments about the mod...(OPTIONAL)]`")
    parser.add_argument("-o", "--output", required=True, type=str, help="The directory to which scripts will be outputted")
    parser.add_argument("-g", "--game-version", required=True, type=str, help="The version of Minecraft")
    parser.add_argument("-l", "--loader", type=str, default="fabric", help="The modloader used for the modpack")
    parser.add_argument("-d", "--include-optional-dependencies", action='store_true', help="Allows inclusion of optional dependencies")
    parser.add_argument("-y", "--yall", action='store_true', help="Inlcudes all optional mods (yes to all optional mods)")
    parser.add_argument("-n", "--nall", action='store_true', help="Excludes all optional mods (no to all optional mods)")
    args = parser.parse_args()

    if args.yall and args.nall:
        print("Both --yall and --nall were flagged. Must flag one or the other.")
        exit(-1)


    # Set globals
    PARAMS["game_versions"] = '["' + args.game_version + '"]'
    PARAMS["loaders"] = '["' + args.loader + '"]'
    INC_OPTIONAL = args.include_optional_dependencies
    if args.yall: REQUIRED_OVERRIDE = True
    if args.nall: REQUIRED_OVERRIDE = False

    if not os.path.exists(args.output): os.makedirs(args.output)

    # Parse list
    mod_list = parse_csv(args.modpack)

    # Get mod information
    required, optional, dependencies, urls = get_all_mod_info(mod_list)

    # Write
    write_all(args.output, required, optional, dependencies, urls)

    print("\nScript generation complete")

    pass


SCRIPTS = {
    "bash.sh": (
# FULL
"""
#!/bin/bash

# Note: For increased parity with Windows Batch Scripts, arrays/dicts will not be used
# Instead, strings of elements separated by semicolons are used for lists, and elements
# will be prefixed by "KEY:" for dicts. 

URLS=""          # dict: MOD_ID:DOWNLOAD_URL;...
DEPENDENCIES=""  # dict: MOD_ID:DEP_ID_1,DEP_ID_2,...;...
OPTIONAL=""      # dict: MOD_ID:NAME,comments or other info;...
DOWNLOAD_LIST="" # list: MOD_ID_1;...

# Used wget if curl not found (https://stackoverflow.com/a/677212)
curl --version >/dev/null 2>&1
if [[ $? -eq 0 ]] ; then
    DOWNLOAD_CMD="curl -O"
else
    DOWNLOAD_CMD="wget"
fi


# Given a dictionary, find the value from a key, return 0 if key found, 1 otherwise
index_dict () { # Params: Dict, Key
    REMAINING=$1

    while [[ -n $REMAINING ]] ; do
        KEY=${REMAINING%%:*}
        
        if [[ $2 == $KEY ]] ; then
            VALUE=${REMAINING%%;*}
            echo ${VALUE#*:}
            return 0
        fi
        
        REMAINING=${REMAINING#*;}
    done

    return 1
}


# Given a list, return 1 if key exists in list, otherwise 0
is_in_list () { # List, Key
    REMAINING=$1

    while [[ -n $REMAINING ]] ; do
        NEXT=${REMAINING%%;*}
        
        if [[ $2 == $NEXT ]] ; then
            return 1
        fi

        REMAINING=${REMAINING#*;}
    done

    return 0
}


# Add to DOWNLOAD_LIST. Returns 1 if already present in the list, 0 otherwise
add_download () { # {Mod ID or Slug}
    VOID=$(is_in_list $DOWNLOAD_LIST $1)

    if [[ $? -eq 1 ]] ; then
        return 1
    else
        DOWNLOAD_LIST="${DOWNLOAD_LIST}${1};"
    fi

    return 0
}


add_download_with_deps () { # {Mod ID or Slug}
    add_download $1


    # Get dependencies, continue if none
    MOD_DEPS="$(index_dict $DEPENDENCIES $1),"
    if [[ $? -eq 1 ]] ; then
        return 0
    fi

    # Add all dependencies
    while [[ -n $MOD_DEPS ]] ; do
        NEXT_DEP=${MOD_DEPS%%,*}

        add_download $NEXT_DEP

        MOD_DEPS=${MOD_DEPS#*,}

    done
}


# Adds a mod formatted like `ID,name,comments...`
handle_opt_mod () {
    REM=$1

    # Handle single line
    MOD_ID=${REM%%:*}
    REM=${REM#*:}
    MOD_NAME=${REM%%,*}
    MOD_COMMENT=${REM#*,}

    is_in_list $DOWNLOAD_LIST $MOD_ID
    [[ $? -eq 1 ]] && return 1 # Skip if already in the download list

    # Get user input
    echo "$MOD_NAME [$MOD_ID]: $MOD_COMMENT"
    echo "    https://modrinth.com/mod/$MOD_ID"

    IN=""
    while [[ $IN != "y" ]] ; do
        read -p "    Use this mod? [y/n]:" IN
        [[ $IN == "n" ]] && return 0
    done

    add_download_with_deps $MOD_ID

    return 0
}

stage=0

# Read mod info from end of file
while IFS= read -r line; do
    [[ -z $line ]] && continue

    if [[ "$line" == \\#* ]] ; then
        if [[ "$line" == "# REQUIRED" ]] ; then
            stage=1
        elif [[ "$line" == "# OPTIONAL" ]] ; then
            stage=2
        elif [[ "$line" == "# DEPENDENCIES" ]] ; then
            stage=3
        elif [[ "$line" == "# URLS" ]] ; then
            stage=4
        fi
        continue
    fi

    if [[ $stage -eq 1 ]] ; then
        DOWNLOAD_LIST="${DOWNLOAD_LIST}${line};"
    elif [[ $stage -eq 2 ]] ; then
        OPTIONAL="${OPTIONAL}${line};"
    elif [[ $stage -eq 3 ]] ; then
        DEPENDENCIES="${DEPENDENCIES}${line};"
    elif [[ $stage -eq 4 ]] ; then
        URLS="${URLS}${line};"
    fi
done < "$0"


# Check for "yall"/"nall" parameters
if [[ $# -ge 1 ]] ; then
    # if yall, download all mods from URLs list
    if [[ $1 == "yall" ]] ; then
        while [[ -n $URLS ]] ; do
            NEXT=${URLS%%;*}
            URLS=${URLS#*;}

            $DOWNLOAD_CMD ${NEXT#*:}
        done
        exit 0
    # If nall, only download from required list, which is the current download list so do nothing
    # If unknown, then specify use
    elif [[ $1 != "nall" ]] ; then
        echo "Use: ./scriptname [yall/nall : optional]"
        echo "     yall: download all optional mods"
        echo "     nall: skip all optional mods"
        exit 1
    fi
# Go through all optional mods, adding them to the download list
else
    while [[ -n $OPTIONAL ]] ; do
        NEXT_OPT=${OPTIONAL%%;*}

        handle_opt_mod "$NEXT_OPT"

        OPTIONAL=${OPTIONAL#*;}
    done
fi


# Download all mods
while [[ -n $DOWNLOAD_LIST ]] ; do
    NEXT=${DOWNLOAD_LIST%%;*}

    DOWNLOAD_LIST=${DOWNLOAD_LIST#*;}

    NEXT_URL=$(index_dict $URLS $NEXT)
    $DOWNLOAD_CMD $NEXT_URL
done

exit 0
""",

# SIMPLIFIED
"""
#!/bin/bash

# Note: For increased parity with Windows Batch Scripts, arrays/dicts will not be used
# Instead, strings of elements separated by semicolons are used for lists, and elements
# will be prefixed by "KEY:" for dicts. 

URLS=""          # dict: MOD_ID:DOWNLOAD_URL;...

# Used wget if curl not found (https://stackoverflow.com/a/677212)
curl --version >/dev/null 2>&1
if [[ $? -eq 0 ]] ; then
    DOWNLOAD_CMD="curl -O"
else
    DOWNLOAD_CMD="wget"
fi

stage=0

# Read mod info from end of file
while IFS= read -r line; do
    [[ -z $line ]] && continue

    if [[ "$line" == \\#* ]] ; then
        if [[ "$line" == "# URLS" ]] ; then
            stage=1
        fi
        continue
    fi

    if [[ $stage -eq 1 ]] ; then
        URLS="${URLS}${line};"
    fi
done < "$0"

# Download from all URLs
while [[ -n $URLS ]] ; do
    NEXT=${URLS%%;*}
    URLS=${URLS#*;}

    $DOWNLOAD_CMD ${NEXT#*:}
done

exit 0
"""
    ),
}

if __name__ == "__main__":
    main()