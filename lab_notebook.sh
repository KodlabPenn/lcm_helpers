# Run this script in your log directory, recursively looks for *.readme and 
# displays them 

# Get readmes
readmes=$(ls -R -r */*.readme)

# Make a tempfile for concatenating and displaying
tmpFile=$(tempfile)

# Coloring for easier test to test differentiation in 'less'
LOGFILEFORMAT="\033[46;1;3;30m"

# Line drawing helper funtion
draw_line(){
    for i in $(seq 1 $1); do echo -e -n "-"; done
}

# Add readmes and headers to tempfile
for readme in $readmes; do 

    let "readmeLength=${#readme}+6"

    draw_line ${readmeLength} >> $tmpFile

    echo -e "\n${LOGFILEFORMAT}   ${readme}   " >> $tmpFile

    draw_line ${readmeLength} >> $tmpFile

    echo -e "\n" >> $tmpFile
    cat $readme >> $tmpFile
    echo -e "\n" >> $tmpFile

done

# Open temp file in less
less -R $tmpFile

# Delete tempfile (would be deleted automatically, but extra safe)
rm $tmpFile
