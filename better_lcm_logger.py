#! /usr/bin/python
""" lcm-logger Python wrapper script. 

This script wraps the lcm-logger to create a particular directory structure and 
also allows for the addition of a README with each run. The directory structure 
is as follows
|-> <DIRECTORY>
|    -> <LOG-DESCRIPTION-AND-ID-AND-TIME>
|          -> <LOG-NAME-AND-TIME>
|          -> <LOG-NAME-AND-TIME>.readme
A typical log structure may look like this
|-> logs
|    -> 2023-04-23x000_GainTuningExperiments
|        -> log00-083545
|        -> log00-083545.readme
|        -> log01-084024
|        -> log01-084024.readme
|        -> log02-084631
|        -> log02-084631.readme
|    -> 2023-04-23x001_FinalGainExperiments
|        -> log00-093347
|        -> log00-093347.readme
|    -> 2023-04-24x000_RobotRunning
|        -> log00-093627
|        -> log00-093627.readme

Requirements:
  lcm-loggger
  nano

Typical usage examples:
  >>  ./better_lcm_logger.py gain tuning
  | Opening log file "logs/2023-04-29x000_GainTuning/log-235959
  | ...
  | ...
  | ^CLogger exiting
  | Keep log? (y/n)  y
  |
  >>  python better_lcm_logger.py robot running --notes --directory logs/robot/
  | Opening log file "logs/robot/2023-04-29x000_RobotRunning/log-235959
  | ...
  | ...
  | ^CLogger exiting
  | Keep log? (y/n)  y
  | Opening README
  |
  >>  python better_lcm_logger.py robot walking
  | Opening log file "logs/2023-04-29x001_RobotWalking/log-115550
  | ...
  | ...
  | ^CLogger exiting
  | Keep log? (y/n)  n
  | Log was not saved.
  |

To make into an executable:
  >>  chmod +x better_lcm_logger.py

Args:
  logname: required 
      a name or short description for the logged experiment
  directory (d): optional, default: "logs/"
      relative or absolute path where log directory and files are to be kept
  notes (n): optional flag, default: "false"
      Including this flag will make the program create/open a readme after the
      experiment for writing notes and comments for later context 
  wait (w): optional flag, default: "false"
      Including this flag will make the program wait until the user presses
      enter to start logging
  notes (p): optional flag, default: "false"
      Including this flag will make the program create/open a readme before an
      experiment and ask for notes before an experiment begins 

"""


import os
import random
import uuid
import string
import subprocess
import argparse
import datetime
import re


def input_yn(prompt):
  """ Wrapper around input() to make it a yes or no question
  
  Args:
    prompt: string for input prompt

  Returns:
    bool: True if the answer was 'y' or 'yes' and False if 'n' or 'no

  Raises:
    ValueError: When the user does not answer yes or no
  """
  while True:
    user_input = input(prompt + "\n    (y/n)\t")
    if user_input.lower() in ['y','yes']:
      return True
    elif user_input.lower() in ['n','no']:
      return False
    else:
      print("Invalid response.")

def check_dir_path(string):
  """ Check if `string` is a directory and ask if one should be made if it is 
  not there. Also, pathify the output

  Args:
    string: directory path to be checked for existence

  Return:
    path: pathified version of the input string

  Raises:
    NotADirectoryError: string can't be directory or user chooses to not make new
      directories
  """
  if os.path.isdir(string):
    return os.path.normpath(string)
  elif(string=="logs" and os.path.isdir("../logs")):
    return os.path.normpath("")
  else:
    user_yn = input_yn("Directory does not exit.\nMake a new directory at\n" + 
                       os.path.normpath(string) + " ?")
    if user_yn:
      os.mkdir(os.path.normpath(string) )
      return os.path.normpath(string)
    else:
      raise NotADirectoryError(string)

# Get arguments from command line
parser = argparse.ArgumentParser(description='Wrapper around LCM logger for added workflow and better directory structure.')
parser.add_argument('logname', metavar='log', type=str, nargs='+',
                    help='log directory name')
parser.add_argument('--directory','-d', type=check_dir_path, default="logs",
                    help='log name')
parser.add_argument('--notes', '-n', action='store_true',
                    help='creates/opens log readme and ask for notes after an experiment ends')
parser.add_argument('--prenotes', '-p', action='store_true',
                    help='creates/opens log readme ask for notes before an experiment begins')
parser.add_argument('--wait', '-w', action='store_true',
                    help='Wait until the user types enter to start logging')

args = parser.parse_args()

# Constants
README_SUFFIX = ".readme"
README_SUFFIX_LEN = len(README_SUFFIX)
LOG_PREFIX = "log"

log_dir_path = ( 
  # Clean input log name/desc
  os.path.normpath(''.join([word.capitalize() for word in args.logname])))
directory = args.directory
do_readme_pre = args.prenotes
do_readme_post = args.notes
do_readme = do_readme_pre or do_readme_post
do_wait = args.wait
current_datetime = datetime.datetime.now()
folder_date = current_datetime.strftime("%Y-%m-%d")

order_index = 0
dir_list = os.listdir(directory)

# Set up simple ordering index to keep sorted folders in chronological order
dir_list = [dir for dir in dir_list if folder_date in dir]
order_index = len(dir_list)

# Skip if first experiement of the day
if order_index:
  # If the last experiment was the same one group logs together 
  # in the same folder
  dir_list.sort()
  if log_dir_path == dir_list[order_index - 1][-len(log_dir_path):]:
    order_index -= 1

# Build the directory for the logs and readmes
relative_path_name = folder_date +"x" + f'{order_index:03d}' + '_' + \
                     log_dir_path
full_path = os.path.join(directory, relative_path_name)

# Make the necessary directories if they don't exist
os.makedirs(full_path, exist_ok=True)

# Get experiment number and time for log
experiment_number = 0

files = os.listdir(full_path)
files = [f for f in files if os.path.isfile(full_path+'/'+f)]

log_numbers = [int(f.split('-')[0][3:]) for f in files if f[:len(LOG_PREFIX)]==LOG_PREFIX]
if log_numbers: 
  experiment_number = max(log_numbers) + 1 
else:
  experiment_number = 0

log_path = current_datetime.strftime(
  LOG_PREFIX + f'{experiment_number:02d}'+"-%H%M%S")

readme_file_path = os.path.join(full_path,log_path + README_SUFFIX)
readme_nano_cmd = ["nano","+10000", readme_file_path ]
try:
  # Run lcm-logger

  print("Directory: ", directory)
  print("Experiment: ",relative_path_name)
  print("Log:", log_path )
  if do_readme:
    with open(readme_file_path, "a") as file:
      print("Inializing README.")  
      file.write("README \n" + relative_path_name + "\n" + log_path + "\n" )
      if do_readme_pre:
        file.write("\nPRE RUN NOTES:  ***************** \n")
    if do_readme_pre:
      subprocess.run(readme_nano_cmd)
  if do_wait:
    input("********************************\n"+
          "********************************\n"+
          "Click enter to start logging..." )
  cmd = ["lcm-logger", os.path.join(full_path,log_path) ]
  process = subprocess.run(cmd, check=True)
except KeyboardInterrupt:
  # Ask if we should keep the log
  if not input_yn("Keep log?"):
    delete_log_cmd = ["rm", os.path.join(full_path,log_path)]
    subprocess.run(delete_log_cmd)
    if do_readme:
      delete_readme_cmd = ["rm", readme_file_path]
      print("X--------------------------------------------------X")
      subprocess.run(["cat", readme_file_path])
      print("X--------------------------------------------------X")
      subprocess.run(delete_readme_cmd)
    print("Log and readme were deleted using ")
    print("\t$", *delete_log_cmd)
    if not os.listdir(full_path):
      delete_directory_cmd = ["rm","-r", full_path]
      subprocess.run(delete_directory_cmd)
      print("Empty directory was deleted using ")
      print("\t$", *delete_directory_cmd)
  else:
    # Make readme and open editor
    if do_readme_post:
      print("Opening README for post run notes.")
      with open(readme_file_path, "a") as file:
        file.write("\nPOST RUN NOTES:  **************** \n")
      subprocess.run(readme_nano_cmd)
    if do_readme:
      print("X--------------------------------------------------X")
      subprocess.run(["cat", readme_file_path])
      print("X--------------------------------------------------X")
      print("Logs at: ", os.path.join(full_path,log_path))