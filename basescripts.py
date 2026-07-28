SCRIPTS = {
    "platform": {
        "bash": (
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

DOWNLOAD_CMD="echo "


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

    if [[ "$line" == \#* ]] ; then
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

    if [[ "$line" == \#* ]] ; then
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
#         "windows-batch": (
# # FULL
# """

# """,
# # SIMPLIFIED
# """

# """
#         )
    }
}