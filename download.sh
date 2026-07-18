#!/bin/bash

URLS=""
DEPENDENCIES=""
OPTIONAL=""
DOWNLOAD_LIST=""

# Given a list like `Key:Value;Key:Value;...`, find the value from a key, return 0 if key found, 1 otherwise
search_list () { # List, Key
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

# Given a list like `Key;Key;...`, return 0 if key exists, 1 otherwise
check_list () { # List, Key
    REMAINING=$1

    while [[ -n $REMAINING ]] ; do
        NEXT=${REMAINING%%;*}
        
        if [[ $2 == $NEXT ]] ; then
            return 0
        fi

        REMAINING=${REMAINING#*;}
    done

    return 1
}

# Add to DOWNLOAD_LIST. Returns 1 if already present in the list, 0 otherwise
add_download () { # {Mod ID or Slug}
    VOID=$(check_list $DOWNLOAD_LIST $1)

    if [[ $? -eq 0 ]] ; then
        return 1
    else
        DOWNLOAD_LIST="${DOWNLOAD_LIST}${1};"
    fi

    return 0
}


# Adds a mod formatted like `ID,name,comments...`
handle_opt_mod () {
    REM=$1

    # Handle single line
    MOD_ID=${REM%%,*}
    REM=${REM#*,}
    MOD_NAME=${REM%%,*}
    MOD_COMMENT=${REM#*,}

    add_download $MOD_ID
    [[ $? -eq 1 ]] && continue # Skip if already in the download list

    # Get user input
    echo "$MOD_ID $MOD_NAME $MOD_COMMENT $MOD_DEPS"
    echo "    https://modrinth.com/mod/$MOD_ID"

    IN=""
    while [[ $IN != "y" ]] ; do
        read -p "    Use this mod? [y/n]:" IN
        [[ $IN == "n" ]] && return 0
    done
    # TODO


    # Get dependencies, continue if none
    MOD_DEPS="$(search_list $DEPENDENCIES $MOD_ID),"
    if [[ $? -eq 1 ]] ; then
        return 0
    fi

    # Add all dependencies
    while [[ -n $MOD_DEPS ]] ; do
        NEXT_DEP=${MOD_DEPS%%,*}

        add_download $NEXT_DEP

        # if [[ $? -eq 0 ]] ; then
        #     echo Added $NEXT_DEP
        # else
        #     echo $NEXT_DEP already in downloads
        # fi

        MOD_DEPS=${MOD_DEPS#*,}

    done

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


# echo $DOWNLOAD_LIST
# echo $OPTIONAL
# echo $DEPENDENCIES
# echo $URLS


while [[ -n $OPTIONAL ]] ; do
    NEXT_OPT=${OPTIONAL%%;*}

    handle_opt_mod "$NEXT_OPT"

    OPTIONAL=${OPTIONAL#*;}
done


echo DOWNLOAD_LIST:
echo "  $DOWNLOAD_LIST"

exit 0


while [[ -n $DOWNLOAD_LIST ]] ; do
    NEXT=${DOWNLOAD_LIST%%;*}

    DOWNLOAD_LIST=${DOWNLOAD_LIST#*;}
    echo "Downloading $NEXT"

    NEXT_URL=$(search_list $URLS $NEXT)
    echo "    $NEXT_URL"
done

exit 0

# REQUIRED
ID3

# OPTIONAL
ID1,name1, This is a mod that does shit
ID2,name2, This is also a mod that does shit

# DEPENDENCIES
ID1:ID2,ID3
ID2:ID3
ID3:

# URLS
ID1:URL1
ID2:URL2
ID3:URL3
