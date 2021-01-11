"""
This script generates an "observing log" for a directory with a set of files
to be reduced by PypeIt.
"""
import time
import os
import shutil
import io       # NOTE: This is *not* pypeit.io

from IPython import embed

import numpy as np

from pypeit.spectrographs import available_spectrographs

def parse_args(options=None, return_parser=False):
    import argparse

    parser = argparse.ArgumentParser(description='Construct an observing log for a set of files '
                                                 'from the provided spectrograph using '
                                                 'PypeItMetaData.',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('spec', type=str,
                        help='A valid spectrograph identifier: {0}'.format(
                                    ', '.join(available_spectrographs)))
    parser.add_argument('-r', '--root', default=os.getcwd(), type=str,
                        help='Root to search for data files.  You can provide the top-level '
                             'directory  (e.g., /data/Kast) or the search string up through the '
                             'wildcard (.e.g, /data/Kast/b).  Use the --extension option to set '
                             'the types of files to search for.  Default is the current working '
                             'directory.')
    parser.add_argument('-k', '--keys', default=False, action='store_true',
                        help='Do not produce the log; simply list the pypeit-specific metadata '
                             'keys available for this spectrograph and their associated header '
                             'cards.  Metadata keys with header cards that are None have no '
                             'simple mapping between keyword and header card.')
    parser.add_argument('-c', '--columns', default='pypeit', type=str,
                        help='A comma-separated list of columns to include in the output table. '
                             'Each column must be a valid pypeit metadata keyword specific to '
                             'this spectrograph (run pypeit_obslog with the -k argument to see '
                             'the valid list).  Additional valid keywords are directory, '
                             'filename, frametype, framebit, setup, calib, and calibbit. '
                             'If \'all\', all columns collected for the pypeit metadata table '
                             'are included.  If \'pypeit\', the columns are the same as those '
                             'included in the pypeit file.')
    parser.add_argument('-b', '--bad_frames', default=False, action='store_true',
                        help='Clean the output of bad frames that cannot be reduced by pypeit.')
    parser.add_argument('-g', '--groupings', default=True, action='store_false',
                        help='Use this option to only determine the frame type.  By default, the '
                             'script groups frames into expected configuration and calibration '
                             'groups, and it adds the default combination groups.')
    parser.add_argument('-i', '--interact', default=False, action='store_true',
                        help='Once the metadata table is created, start an embedded IPython '
                             'session that you can use to interact with the table (an '
                             'Astropy.Table called fitstbl) directly.')
    parser.add_argument('-s', '--sort', default='mjd', type=str,
                        help='Metadata keyword (pypeit-specific) to use to sort the output table.')
    parser.add_argument('-e', '--extension', default='.fits',
                        help='File extension; compression indicators (e.g. .gz) not required.')
    parser.add_argument('-d', '--output_path', default=os.getcwd(),
                        help='Path to top-level output directory.')
    parser.add_argument('-o', '--overwrite', default=False, action='store_true',
                        help='Overwrite any existing files/directories')
    parser.add_argument('-f', '--file', default=None, type=str,
                        help='Name for the ascii output file.  Any leading directory path is '
                             'stripped; use -d to set the output directory.  If None, the table '
                             'is just printed to stdout.  If set to \'default\', the file is set '
                             'to [spectrograph].obslog.  Note the file will *not* be written if '
                             'you also include the -i option to embed and interact with the table '
                             '(you can write the table using the astropy.table.Table.write method '
                             'in the embedded IPython session).  The table is always written in '
                             'ascii format using format=ascii.fixed_with for the call to '
                             'Astropy.table.Table.write .')

    if return_parser:
        return parser

    return parser.parse_args() if options is None else parser.parse_args(options)


def main(args):

    from pypeit.spectrographs.util import load_spectrograph
    from pypeit.pypeitsetup import PypeItSetup

    # Check that input spectrograph is supported
    if args.spec not in available_spectrographs:
        raise ValueError('Instrument \'{0}\' unknown to PypeIt.\n'.format(args.spec)
                         + '\tOptions are: {0}\n'.format(', '.join(available_spectrographs))
                         + '\tSelect an available instrument or consult the documentation '
                         + 'on how to add a new instrument.')

    if args.keys:
        # Only print the metadata to header card mapping
        load_spectrograph(args.spec).meta_key_map()
        return

    # Generate the metadata table
    ps = PypeItSetup.from_file_root(args.root, args.spec, extension=args.extension)
    ps.run(setup_only=True, write_files=False, groupings=args.groupings,
           clean_config=args.bad_frames)

    # Check the file can be written (this is here because the spectrograph
    # needs to be defined first)
    _file = args.file
    if _file == 'default':
        _file = f'{ps.spectrograph.name}.obslog'
    if _file is not None:
        _odir, _file = os.path.split(_file)
        if len(_odir) == 0:
            _file = os.path.join(args.output_path, _file)
        if not args.interact and os.path.isfile(_file) and not args.overwrite:
            raise FileExistsError(f'{_file} already exists.  Use -o to overwrite.')

    # Write/Print the data
    header = ['Auto-generated PypeIt Observing Log',
              '{0}'.format(time.strftime("%a %d %b %Y %H:%M:%S",time.localtime())),
              f'Root file string: {args.root}']
    ps.fitstbl.write(output=_file, columns=args.columns, sort_col=args.sort,
                     overwrite=args.overwrite, header=header)

