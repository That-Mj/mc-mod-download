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



# REQUIRED
mOgUt4GM
P7dR8mSH
eXts2L7r
Wb5oqrBJ
pMBcsVIg
ZLKQjA7t
L4pt5egz
EsAfCjCV
qQyHxfxd
UIexcMP1
7diJQfvM
yXAvIk0x
2M01OLQq
xv94TkTM
fuuu3xnx
AANobbMI
gvQqBUqZ
uXXizFIs
NNAgCjsB
ONZm0H7Y
yBW8D80W
1IjD5062


# OPTIONAL
wGoQDPN5:Vivecraft,bullshit
Nv2fQJo5:ReplayMod,bullshit
TQTTVgYE:Carpet,bullshit
aC3cM3Vq:Mouse Tweaks,bullshit
5ZwdcRci:ImmediatelyFast,bullshit
uCdwusMi:Distant Horizons,bullshit
fxxUqruK:voxy,bullshit
xT0lnNE9:Voxy WorldGen,bullshit
YL57xq9U:Iris Shaders,bullshit
9eGKb6K1:Simple Voice Chat,bullshit
qsSP2ZZ0:Voice Chat Interaction,bullshit
qyVF9oeo:Sound Physics Remastered,bullshit


# DEPENDENCIES
xT0lnNE9:9s6osm5g,fxxUqruK
qsSP2ZZ0:9eGKb6K1

ID:URL


# URLS
P7dR8mSH:https://cdn.modrinth.com/data/P7dR8mSH/versions/lVXlbH4w/fabric-api-0.155.2%2B26.2.jar
mOgUt4GM:https://cdn.modrinth.com/data/mOgUt4GM/versions/njXb639R/modmenu-20.0.1.jar
eXts2L7r:https://cdn.modrinth.com/data/eXts2L7r/versions/NDqH16LT/placeholder-api-3.1.0-beta.1%2B26.2.jar
wGoQDPN5:https://cdn.modrinth.com/data/wGoQDPN5/versions/VrqKDtZn/vivecraft-26.2-1.3.15-fabric.jar
Nv2fQJo5:https://cdn.modrinth.com/data/Nv2fQJo5/versions/5YS1OgDP/replaymod-26.2-2.6.27.jar
TQTTVgYE:https://cdn.modrinth.com/data/TQTTVgYE/versions/bGrLxJ8v/fabric-carpet-26.2%2Bv260616.jar
Wb5oqrBJ:https://cdn.modrinth.com/data/Wb5oqrBJ/versions/bASLtZKx/chat_heads-1.2.5-fabric-26.1.jar
pMBcsVIg:https://cdn.modrinth.com/data/pMBcsVIg/versions/CHYrFP5J/locator_lodestones-1.5.3%2B26.2%2BA.jar
ZLKQjA7t:https://cdn.modrinth.com/data/ZLKQjA7t/versions/904miTgt/pneumonocore-1.3.1%2B26.2%2BA.jar
L4pt5egz:https://cdn.modrinth.com/data/L4pt5egz/versions/OPUaj8dP/locator-heads-2.4.2.jar
EsAfCjCV:https://cdn.modrinth.com/data/EsAfCjCV/versions/uo5bAN1Y/appleskin-fabric-mc26.2-3.0.10.jar
qQyHxfxd:https://cdn.modrinth.com/data/qQyHxfxd/versions/uiY9tUaj/NoChatReports-FABRIC-26.2-v2.20.1.jar
UIexcMP1:https://cdn.modrinth.com/data/UIexcMP1/versions/SRaSZqo0/BorderlessFullscreen-v2.4.1-mc26.2.jar
7diJQfvM:https://cdn.modrinth.com/data/7diJQfvM/versions/wLWbSes5/DeleteWorldsToTrash-v26.2.0-mc26.2.x-Fabric.jar
yXAvIk0x:https://cdn.modrinth.com/data/yXAvIk0x/versions/lHq8aTGm/scribble-2.1.0-beta1%2Bmc26.2.jar
2M01OLQq:https://cdn.modrinth.com/data/2M01OLQq/versions/IHUNStdu/shulkerboxtooltip-fabric-5.4.0%2B26.2.jar
aC3cM3Vq:https://cdn.modrinth.com/data/aC3cM3Vq/versions/jOiTBIaB/MouseTweaks-fabric-mc26.2-2.31.jar
xv94TkTM:https://cdn.modrinth.com/data/xv94TkTM/versions/rAp2jljs/Controlling-fabric-26.2-26.2.2.jar
fuuu3xnx:https://cdn.modrinth.com/data/fuuu3xnx/versions/bvFby61J/Searchables-fabric-26.2-1.0.1.jar
AANobbMI:https://cdn.modrinth.com/data/AANobbMI/versions/2Yom1N68/sodium-fabric-0.9.1%2Bmc26.2.jar
gvQqBUqZ:https://cdn.modrinth.com/data/gvQqBUqZ/versions/UPNexAfy/lithium-fabric-0.25.2%2Bmc26.2.jar
uXXizFIs:https://cdn.modrinth.com/data/uXXizFIs/versions/d5ddUdiB/ferritecore-9.0.0-fabric.jar
NNAgCjsB:https://cdn.modrinth.com/data/NNAgCjsB/versions/iiF6U3Ne/entityculling-fabric-1.10.5-mc26.2.jar
ONZm0H7Y:https://cdn.modrinth.com/data/ONZm0H7Y/versions/IDqHHWrF/bbe-fabric-1.3.7%2Bmc26.2.jar
5ZwdcRci:https://cdn.modrinth.com/data/5ZwdcRci/versions/uJHxuQxy/ImmediatelyFast-Fabric-1.16.2%2B26.2.jar
uCdwusMi:https://cdn.modrinth.com/data/uCdwusMi/versions/gBf0SaV1/DistantHorizons-3.2.0-b-26.2-fabric-neoforge.jar
fxxUqruK:https://cdn.modrinth.com/data/fxxUqruK/versions/zZX86mbc/voxy-0.2.18-beta.jar
xT0lnNE9:https://cdn.modrinth.com/data/xT0lnNE9/versions/II0QK5sq/Voxy%20World%20Gen%20V2-fabric-26.2-2.4.2.jar
9s6osm5g:https://cdn.modrinth.com/data/9s6osm5g/versions/Nv3xnWXd/cloth-config-26.2.155.jar
YL57xq9U:https://cdn.modrinth.com/data/YL57xq9U/versions/oaD6KQls/iris-fabric-1.11.2%2Bmc26.2.jar
yBW8D80W:https://cdn.modrinth.com/data/yBW8D80W/versions/jBLH7Qy8/lambdynamiclights-4.12.2%2B26.2.jar
1IjD5062:https://cdn.modrinth.com/data/1IjD5062/versions/mgUN5Xz2/continuity-3.0.1%2B26.2.jar
9eGKb6K1:https://cdn.modrinth.com/data/9eGKb6K1/versions/3SOh5iiX/voicechat-fabric-2.6.21%2B26.2.jar
qsSP2ZZ0:https://cdn.modrinth.com/data/qsSP2ZZ0/versions/luUS5Hod/vcinteraction-fabric-1.0.8%2B26.2.jar
qyVF9oeo:https://cdn.modrinth.com/data/qyVF9oeo/versions/d8iioMMp/sound-physics-remastered-fabric-1.5.1%2B26.2.jar

