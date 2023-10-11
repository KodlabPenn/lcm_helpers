#!/usr/bin/python

# Heavily based on libbot2's implementation: https://github.com/libbot2/libbot2
# As such, this file is licensed under the Lesser General Public License (LGPL)
# The license can be found here, https://www.gnu.org/licenses/lgpl-3.0.html

# The intent of this module is to find and store the different available lcm
# types for use in lcm data decoding

# This works best if the lcm types are on your python path (the default uses
# sys.path)

import re
import os
import sys
import pyclbr

def find_lcmtypes(dir_or_dirs, debug=False):
    lcmtypes = []
    if isinstance(dir_or_dirs,list):
        for dir in dir_or_dirs:
            lcmtypes += find_lcmtypes_in_directory(dir, debug)
        return lcmtypes
    else:
        return find_lcmtypes_in_directory(dir_or_dirs, debug)

def find_lcmtypes_in_directory(dir_name, debug=False, cache=False):
    alpha_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")
    valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
    lcmtypes = []
    regex = re.compile("_get_packed_fingerprint")
    
    for root, dirs, files in os.walk(dir_name):
        subdirs = root[len(dir_name):].split(os.sep)
        subdirs = [ s for s in subdirs if s ]

        python_package = ".".join(subdirs)

        for fname in files:
            if not fname.endswith(".py"):
                continue
            mod_basename = fname[:-3]
            valid_modname = True
            for c in mod_basename:
                if c not in valid_chars:
                    valid_modname = False
                    break
            if mod_basename[0] not in alpha_chars:
                valid_modname = False
            if not valid_modname:
                continue
            # quick regex test -- check if the file contains the 
            # word "_get_packed_fingerprint"
            full_fname = os.path.join(root, fname)
            try: 
                with open(full_fname, "r") as f:
                  contents = f.read()
            except IOError:
                continue
            except Exception as e:
                if(debug):
                    print(f"For file name: {full_fname}")
                    print(f"\tignoring unexpected error: {e}")
                continue
            if not regex.search(contents):
                continue
                
            # More thorough check to see if the file corresponds to a
            # LCM type module generated by lcm-gen.  Parse the 
            # file using pyclbr, and check if it contains a class
            # with the right name and methods
            if python_package:
                modname = "%s.%s" % (python_package, mod_basename)
            else:
                modname = mod_basename
            try:
                klass = pyclbr.readmodule(modname)[mod_basename]
                if "decode" in klass.methods and \
                    "_get_packed_fingerprint" in klass.methods:

                    lcmtypes.append(modname)
            except ImportError:
                continue
            except KeyError:
                continue
            # only recurse into subdirectories that correspond to python 
            # packages (i.e., they contain a file named "__init__.py")
            subdirs_to_traverse = [ subdir_name for subdir_name in dirs \
                    if os.path.exists(os.path.join(root, subdir_name, "__init__.py")) ]
            del dirs[:]
            dirs.extend(subdirs_to_traverse)
    return lcmtypes

def make_lcmtype_dictionary(dir_or_dirs=sys.path, debug=False):
    """Create a dictionary of LCM types keyed by fingerprint.

    Searches the specified python package directories for modules 
    corresponding to LCM types, imports all the discovered types into the
    global namespace, and returns a dictionary mapping packed fingerprints
    to LCM type classes.

    The primary use for this dictionary is to automatically identify and 
    decode an LCM message.

    """
    lcmtypes = find_lcmtypes(dir_or_dirs, debug)

    result = {}

    for lcmtype_name in lcmtypes:
        try:
            __import__(lcmtype_name)
            mod = sys.modules[lcmtype_name]
            type_basename = lcmtype_name.split(".")[-1]
            klass = getattr(mod, type_basename)
            fingerprint = klass._get_packed_fingerprint()
            result[fingerprint] = klass
            #print "importing %s" % lcmtype_name
        except:
            if(debug):
                print(f"Error importing {lcmtype_name}")
    return result

# def cache_type_dictionary()
 
if __name__ == "__main__":
    import binascii
    print("Searching for LCM types...")
    lcmtypes = make_lcmtype_dictionary(sys.path)
    num_types = len(lcmtypes)
    print("Found %d type%s" % (num_types, num_types==1 and "" or "s"))
    for fingerprint, klass in lcmtypes.items():
        print(binascii.hexlify(fingerprint), klass.__module__)