import scan_for_lcmtypes as scan
import lcm  # LCM message support
import argparse
import numpy as np
import sys
import pickle
import os
import pandas as pd
import glob

def unpack_msg(msg):
    """Unpack an LCM message into a dictionary"""
    def valid_variable(name):
        specials = ["decode", "encode", "get_hash"]
        return not (name[:1] == "_" or name in specials)
    variables = [variable for variable in dir(msg) if valid_variable(variable)]
    unpack = {}
    for variable in variables:
        att = getattr(msg, variable)
        try:
            iterator = iter(att)
        except TypeError:
            unpack[variable] = att
        else:
            unpack[variable] = list(att)
    return unpack

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

def get_lcm_channel_data(lcm_log: lcm.EventLog, channel: str, lcm_type_for_decode, trim_front: int = 0, use_nparray: bool = False):
    """Gather data from `channel` and return as dictionary"""
    data = {slot: [] for slot in lcm_type_for_decode.__slots__}
    count = 0
    for event in lcm_log:
        if event.channel == channel:
            if count < trim_front:
                continue
            message = lcm_type_for_decode.decode(event.data)
            content = unpack_msg(message)
            for key, value in content.items():
                data[key].append(value)
    
    if use_nparray:
        for key, value in data.items():
            data[key] = np.array(value)
    return data

def get_lcm_data(lcm_log: lcm.EventLog, lcm_type_dictionary=None, channels=None, trim_front: int = 0, use_nparray: bool = False):
    """Gather data from all channels and return as dictionary"""
    if lcm_type_dictionary is None:
        lcm_type_dictionary = scan.make_lcmtype_dictionary() #Make the dictionary using the sys path
    # data = collections.defaultdict(dict)
    data = {}
    # data = {slot: [] for slot in lcm_type_for_decode.__slots__}
    
    count = 0
    time_key = "time_received"
    print("Channels:")
    for event in lcm_log:
        if event.channel == "LCM_TUNNEL_INTROSPECT":
            continue
        if count < trim_front:
            continue
        if channels is not None and event.channel not in channels:
            continue
        fingerprint = event.data[:8]
        lcm_type_for_decode = lcm_type_dictionary.get(fingerprint)
        if lcm_type_for_decode is None:
            print(event.channel, "type not found")
            continue
        if event.channel not in data:
            print("\t" + event.channel)
            data[event.channel] = {slot: [] for slot in lcm_type_for_decode.__slots__}
            data[event.channel][time_key] = []
            
        message = lcm_type_for_decode.decode(event.data)
        content = unpack_msg(message)
        for key, value in content.items():
            data[event.channel][key].append(value)
        data[event.channel][time_key].append(event.timestamp)
    print("Messages:")
    for key_channel, channel_dict in data.items():
        for key, value in channel_dict.items():
            print("\t" + key_channel+"/"+key)
            if use_nparray:
                data[key_channel][key] = np.array(value)
    return data

def prepare_data_for_csv(D):
    # Find all dictionary keys that aren't 1-D
    not_1D = []
    all_shapes = []
    for key in D:
        data_shape = D[key].shape

        # If they're not 1-D,
        if (len(data_shape) > 1):
            not_1D.append(key)

    # Fix all non-1D Data by making new keys
    # For all sets of non 1-D Data
    for i in range(len(not_1D)):

        # Iterate through each dimension of the non 1-D set
        for ii in range(D[not_1D[i]].shape[1]):
            # Make a new key from the 1-D Data iteratively
            D[str(str(not_1D[i]) + "/" + str(ii))] = D[not_1D[i]][:, ii]

        # Remove the multi-dimensional key
        D.pop(not_1D[i])


def to_csv(D, file_name):
    prepare_data_for_csv(D)
    data = pd.DataFrame.from_dict(D)
    data.to_csv(file_name + ".csv", index=False)


if __name__== "__main__":

    # Parse Log File Argument
    parser = argparse.ArgumentParser(description='create plot from log.')
    parser.add_argument('log', metavar='L', type=str, nargs='+',
                        help='log file name')
    parser.add_argument('-l','--lcm_directory', metavar='L', type=str, nargs='*',
                        help='Directory(s) containing lcm_types', default=sys.path)
    parser.add_argument('-c','--csv', action='store_true',
                        help="Enables CSV output.")
    parser.add_argument('-y','--sync', type=str, nargs=1, default=[""], 
                        help="Syncing message for " + \
                        "consolidating csv's. Message should be named the " + \
                        "same in all the channels should be synchronized" )
    parser.add_argument('-p','--pickle', action='store_true',
                        help="Enables Pickle output or clean up")
    parser.add_argument("--clean", action='store_true', 
                        help="Deletes both pickles and csvs for this log" + \
                          " unless csv flag(-c) or pickle flag(-p) is present.")
    parser.add_argument('-q','--quiet', action='store_true',
                        help="Reduces the print messages")
    parser.add_argument('-k', '--channels', type=str, nargs="+", default=None,
                        help="Choose which channels to include in the data." + \
                          "By default includes all the channels.")

    args = parser.parse_args()
    filenames = args.log
    
    #Locally redefine print to do nothing to stop spew
    if args.quiet:
        def print(*args,**kwargs):
            pass

    # Delete any previously made csv or pickles,     
    if args.clean:
        print("\nClean flag detected no outputs will be produced.\n")
        outputs_to_clean = []
        for filename in filenames:
            if args.csv or not (args.csv or args.pickle):
                outputs_to_clean += glob.glob(filename + '*.csv')
            if args.pickle or not (args.csv or args.pickle):
                outputs_to_clean += glob.glob(filename + '*.pickle')
        if outputs_to_clean:        
            print("Files marked for deletion:")
            for out in outputs_to_clean:
                print("\t" + out)
            if input_yn("Delete these files?"):
                for out in outputs_to_clean:
                    os.remove(out)
                print("\nFiles were deleted.")
            else:
                print("\nFiles were NOT deleted.")
        else:
            print("No csv's or pickles found. Exiting.")
        exit()

    dirs_for_lcmtypes = args.lcm_directory
    sync_message_name = args.sync[0]
    lcm_types = scan.make_lcmtype_dictionary(dirs_for_lcmtypes)

    for filename in filenames: # Per log given by user
        log = lcm.EventLog(filename, "r")
        data = get_lcm_data(log, use_nparray=True, channels=args.channels)

        if(args.pickle):
            with open(filename + '.pickle', 'wb') as handle:
                print("Pickled data")
                pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
        if(args.csv): #Must be done last since python uses references
            if(sync_message_name):
                channels_to_sync = []
                number_of_cols = 1
                sync_arrays = []
                data_frames = []
                print("\nSyncing message found in the following channels:")
                for channel, subdata in data.items():
                    if sync_message_name in subdata:
                        print( "\t" + channel)
                        channels_to_sync.append(channel)
                        sync_arrays.append(subdata[sync_message_name])
                        prepare_data_for_csv(subdata)
                        number_of_cols += len(subdata)-1
                        for key in list(subdata.keys()):
                            if(key == sync_message_name):
                                indices = subdata.pop(sync_message_name)
                                continue
                            subdata[channel + "/" + key ] = subdata.pop(key)
                        data_frames.append(pd.DataFrame(subdata,index=indices))
                    else:
                        to_csv(subdata, filename + ".." + channel)
                print("\nSyncing...\n")
                merged_data = pd.concat(data_frames, axis=1).sort_index(kind="mergesort")
                merged_data.to_csv(filename + ".csv", index=True, index_label=sync_message_name)
                
            else:
                for channel, subdata in data.items():
                    #Ubuntu sort in ls ignores dashes and underscores, but not periods
                    #  ".." helps to keep the csvs all together so the channels are known
                    to_csv(subdata, filename + ".." + channel)
            print("CSV's saved")
