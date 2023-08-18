# Run this script in your log directory, recursively looks for *.readme and 
# displays them 

# Handling '-h' option for help string
while getopts ":h" option; do
   case $option in
      h) # display Help
         echo "This script creates a lab notebook view of files ending in '.readmes'"
         echo "Run this script in your logs directory and it will recursively look"
         echo "through the tree"
         echo 
         echo "Syntax: lab_notebook.sh [-h]"
         echo "options:"
         echo "    h    Print this help"
         exit;;
     \?) # incorrect option
         echo "Error: Invalid option, use '-h' "
         exit;;
   esac
done

# Get readmes
readmes="$(ls -R -r *.readme) "
readmes+=$(ls -R -r */*.readme)

# Make a tempfile for concatenating and displaying
tmpFile=$(tempfile)

# Coloring for easier test to test differentiation in 'less'
LOGFILEFORMAT="\033[3;33m"

# Line drawing helper funtion
draw_line(){
    for i in $(seq 1 $1); do echo -e -n "${LOGFILEFORMAT}-"; done
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
