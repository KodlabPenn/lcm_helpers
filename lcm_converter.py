import scan_for_lcmtypes as scan
import lcm  # LCM message support
import argparse
import numpy as np
import sys
import pickle
import os
import pandas as pd

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

def get_lcm_data(lcm_log: lcm.EventLog, lcm_type_dictionary=None, trim_front: int = 0, use_nparray: bool = False):
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

def to_csv(D, file_name):
    # Find all dictionary keys that aren't 1-D
    Not_1D = []
    all_shapes = []
    for key in D:
        data_shape = D[key].shape

        # If they're not 1-D,
        if (len(data_shape) > 1):
            Not_1D.append(key)

    # Fix all non-1D Data by making new keys
    # For all sets of non 1-D Data
    for i in range(len(Not_1D)):

        # Iterate through each dimension of the non 1-D set
        for ii in range(D[Not_1D[i]].shape[1]):
            # Make a new key from the 1-D Data iteratively
            D[str(str(Not_1D[i]) + "/" + str(ii))] = D[Not_1D[i]][:, ii]

        # Remove the multi-dimensional key
        D.pop(Not_1D[i])

    data = pd.DataFrame.from_dict(D)
    data.to_csv(file_name + ".csv", index=False)


if __name__== "__main__":

    # Parse Log File Argument
    parser = argparse.ArgumentParser(description='create plot from log.')
    parser.add_argument('log', metavar='L', type=str, nargs='+',
                        help='log file name')
    parser.add_argument('-d','--directory', metavar='L', type=str, nargs='*',
                        help='Directory containing lcm_types', default=sys.path)
    parser.add_argument('-c','--csv', action='store_true',
                        help="Enables CSV output")
    parser.add_argument('-p','--pickle', action='store_true',
                        help="Enables Pickle output")
    parser.add_argument("--clean", action='store_true', 
                        help="Deletes pickle and/or csvs")

    args = parser.parse_args()
    filenames = args.log
    dirs_for_lcmtypes = args.directory

    lcm_types = scan.make_lcmtype_dictionary(dirs_for_lcmtypes)
    for filename in filenames:
        log = lcm.EventLog(filename, "r")
        data = get_lcm_data(log,use_nparray=True)

        if(args.pickle):
            with open(filename + '.pickle', 'wb') as handle:
                print("Pickled data")
                pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)
        if(args.csv): #Must be done last since python uses references
            for channel, subdata in data.items():
                #Ubuntu sort in ls ignores dashes and underscores, but not periods
                #  ".." helps to keep the csvs all together so the channels are known
                to_csv(subdata, filename + ".." + channel)
            print("CSV's saved")
