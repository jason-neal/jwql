"""Various functions to generate Bokeh objects to be used by the ``views`` of
the ``jwql`` app.

This module contains several functions that instantiate BokehTemplate objects
to be rendered in ``views.py`` for use by the ``jwql`` app.

Authors
-------

    - Gray Kanarek

Use
---

    The functions within this module are intended to be imported and
    used by ``views.py``, e.g.:

    ::
        from .data_containers import get_mast_monitor
"""

import glob
import os

from astropy.io import fits
import numpy as np

from jwql.preview_image.preview_image import PreviewImage
from jwql.utils.utils import get_config, filename_parser, MONITORS

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))
FILESYSTEM_DIR = os.path.join(get_config()['jwql_dir'], 'filesystem')
PACKAGE_DIR = os.path.dirname(__location__.split('website')[0])
REPO_DIR = os.path.split(PACKAGE_DIR)[0]


def get_acknowledgements():
    """Returns a list of individuals who are acknowledged on the
    ``about`` page.

    The list is generated by reading in the contents of the ``jwql``
    ``README`` file.  In this way, the website will automatically
    update with updates to the ``README`` file.

    Returns
    -------
    acknowledgements : list
        A list of individuals to be acknowledged.
    """

    # Locate README file
    readme_file = os.path.join(REPO_DIR, 'README.md')

    # Get contents of the README file
    with open(readme_file, 'r') as f:
        data = f.readlines()

    # Find where the acknowledgements start
    for i, line in enumerate(data):
        if 'Acknowledgments' in line:
            index = i

    # Parse out the list of individuals
    acknowledgements = data[index + 1:]
    acknowledgements = [item.strip().replace('- ', '').split(' [@')[0].strip() for item in acknowledgements]

    return acknowledgements


def get_dashboard_components():
    """Build and return a dictionary containing components needed for
    the dashboard.

    Returns
    -------
    dashboard_components : dict
        A dictionary containing components needed for the dashboard.
    """

    output_dir = get_config()['outputs']
    name_dict = {'': '',
                 'monitor_mast': 'Database Monitor',
                 'database_monitor_jwst': 'JWST',
                 'database_monitor_caom': 'JWST (CAOM)',
                 'monitor_filesystem': 'Filesystem Monitor',
                 'filecount_type': 'Total File Counts by Type',
                 'size_type': 'Total File Sizes by Type',
                 'filecount': 'Total File Counts',
                 'system_stats': 'System Statistics'}

    dashboard_components = {}
    for dir_name, subdir_list, file_list in os.walk(output_dir):
        monitor_name = os.path.basename(dir_name)
        dashboard_components[name_dict[monitor_name]] = {}
        for fname in file_list:
            if 'component' in fname:
                full_fname = '{}/{}'.format(monitor_name, fname)
                plot_name = fname.split('_component')[0]

                # Get the div
                html_file = full_fname.split('.')[0] + '.html'
                with open(os.path.join(output_dir, html_file)) as f:
                    div = f.read()

                # Get the script
                js_file = full_fname.split('.')[0] + '.js'
                with open(os.path.join(output_dir, js_file)) as f:
                    script = f.read()
                dashboard_components[name_dict[monitor_name]][name_dict[plot_name]] = [div, script]

    return dashboard_components


def get_filenames_by_instrument(instrument):
    """Returns a list of paths to files that match the given
    ``instrument``.

    Parameters
    ----------
    instrument : str
        The instrument of interest (e.g. `FGS`).

    Returns
    -------
    filepaths : list
        A list of full paths to the files that match the given
        instrument.
    """

    # Query files from MAST database
    # filepaths, filenames = DatabaseConnection('MAST', instrument=instrument).\
    #     get_files_for_instrument(instrument)

    # Find all of the matching files in filesytem
    # (TEMPORARY WHILE THE MAST STUFF IS BEING WORKED OUT)
    instrument_match = {'FGS': 'guider',
                        'MIRI': 'mir',
                        'NIRCam': 'nrc',
                        'NIRISS': 'nis',
                        'NIRSpec': 'nrs'}
    search_filepath = os.path.join(FILESYSTEM_DIR, '*', '*.fits')
    filepaths = [f for f in glob.glob(search_filepath) if instrument_match[instrument] in f]

    return filepaths


def get_header_info(file):
    """Return the header information for a given ``file``.

    Parameters
    ----------
    file : str
        The name of the file of interest.

    Returns
    -------
    header : str
        The primary FITS header for the given ``file``.
    """

    dirname = file[:7]
    fits_filepath = os.path.join(FILESYSTEM_DIR, dirname, file)
    header = fits.getheader(fits_filepath, ext=0).tostring(sep='\n')

    return header


def get_image_info(file_root, rewrite):
    """Build and return a dictionary containing information for a given
    ``file_root``.

    Parameters
    ----------
    file_root : str
        The rootname of the file of interest.
    rewrite : bool
        ``True`` if the corresponding JPEG needs to be rewritten,
        ``False`` if not.

    Returns
    -------
    image_info : dict
        A dictionary containing various information for the given
        ``file_root``.
    """

    # Initialize dictionary to store information
    image_info = {}
    image_info['all_jpegs'] = []
    image_info['suffixes'] = []
    image_info['num_ints'] = {}

    preview_dir = os.path.join(get_config()['jwql_dir'], 'preview_images')

    # Find all of the matching files
    dirname = file_root[:7]
    search_filepath = os.path.join(FILESYSTEM_DIR, dirname, file_root + '*.fits')
    image_info['all_files'] = glob.glob(search_filepath)

    for file in image_info['all_files']:

        # Get suffix information
        suffix = os.path.basename(file).split('_')[4].split('.')[0]
        image_info['suffixes'].append(suffix)

        # Determine JPEG file location
        jpg_dir = os.path.join(preview_dir, dirname)
        jpg_filename = os.path.basename(os.path.splitext(file)[0] + '_integ0.jpg')
        jpg_filepath = os.path.join(jpg_dir, jpg_filename)

        # Check that a jpg does not already exist. If it does (and rewrite=False),
        # just call the existing jpg file
        if os.path.exists(jpg_filepath) and not rewrite:
            pass

        # If it doesn't, make it using the preview_image module
        else:
            if not os.path.exists(jpg_dir):
                os.makedirs(jpg_dir)
            im = PreviewImage(file, 'SCI')
            im.output_directory = jpg_dir
            im.make_image()

        # Record how many integrations there are per filetype
        search_jpgs = os.path.join(preview_dir, dirname, file_root + '_{}_integ*.jpg'.format(suffix))
        num_jpgs = len(glob.glob(search_jpgs))
        image_info['num_ints'][suffix] = num_jpgs

        image_info['all_jpegs'].append(jpg_filepath)

    return image_info


def get_proposal_info(filepaths):
    """Builds and returns a dictionary containing various information
    about the proposal(s) that correspond to the given ``filepaths``.

    The information returned contains such things as the number of
    proposals, the paths to the corresponding thumbnails, and the total
    number of files.

    Parameters
    ----------
    filepaths : list
        A list of full paths to files of interest.

    Returns
    -------
    proposal_info : dict
        A dictionary containing various information about the
        proposal(s) and files corresponding to the given ``filepaths``.
    """

    proposals = list(set([f.split('/')[-1][2:7] for f in filepaths]))
    thumbnail_dir = os.path.join(get_config()['jwql_dir'], 'thumbnails')
    thumbnail_paths = []
    num_files = []
    for proposal in proposals:
        thumbnail_search_filepath = os.path.join(thumbnail_dir, 'jw{}'.format(proposal), 'jw{}*rate*.thumb'.format(proposal))
        thumbnail = glob.glob(thumbnail_search_filepath)
        if len(thumbnail) > 0:
            thumbnail = thumbnail[0]
            thumbnail = '/'.join(thumbnail.split('/')[-2:])
        thumbnail_paths.append(thumbnail)

        fits_search_filepath = os.path.join(FILESYSTEM_DIR, 'jw{}'.format(proposal), 'jw{}*.fits'.format(proposal))
        num_files.append(len(glob.glob(fits_search_filepath)))

    # Put the various information into a dictionary of results
    proposal_info = {}
    proposal_info['num_proposals'] = len(proposals)
    proposal_info['proposals'] = proposals
    proposal_info['thumbnail_paths'] = thumbnail_paths
    proposal_info['num_files'] = num_files

    return proposal_info


def split_files(file_list, page_type):
    """JUST FOR USE DURING DEVELOPMENT WITH FILESYSTEM

    Splits the files in the filesystem into "unlooked" and "archived",
    with the "unlooked" images being the most recent 10% of files.
    """
    exp_times = []
    for file in file_list:
        hdr = fits.getheader(file, ext=0)
        exp_start = hdr['EXPSTART']
        exp_times.append(exp_start)

    exp_times_sorted = sorted(exp_times)
    i_cutoff = int(len(exp_times) * .1)
    t_cutoff = exp_times_sorted[i_cutoff]

    mask_unlooked = np.array([t < t_cutoff for t in exp_times])

    if page_type == 'unlooked':
        print('ONLY RETURNING {} "UNLOOKED" FILES OF {} ORIGINAL FILES'.format(len([m for m in mask_unlooked if m]), len(file_list)))
        return [f for i, f in enumerate(file_list) if mask_unlooked[i]]
    elif page_type == 'archive':
        print('ONLY RETURNING {} "ARCHIVED" FILES OF {} ORIGINAL FILES'.format(len([m for m in mask_unlooked if not m]), len(file_list)))
        return [f for i, f in enumerate(file_list) if not mask_unlooked[i]]


def thumbnails(inst, proposal=None):
    """Generate a page showing thumbnail images corresponding to
    activities, from a given ``proposal``

    Parameters
    ----------
    inst : str
        Name of JWST instrument
    proposal : str (optional)
        Number of APT proposal to filter

    Returns
    -------
    dict_to_render : dict
        Dictionary of parameters for the thumbnails
    """

    filepaths = get_filenames_by_instrument(inst)

    # JUST FOR DEVELOPMENT
    # Split files into "archived" and "unlooked"
    if proposal is not None:
        page_type = 'archive'
    else:
        page_type = 'unlooked'
    filepaths = split_files(filepaths, page_type)

    # Determine file ID (everything except suffix)
    # e.g. jw00327001001_02101_00002_nrca1
    full_ids = set(['_'.join(f.split('/')[-1].split('_')[:-1]) for f in filepaths])

    # If the proposal is specified (i.e. if the page being loaded is
    # an archive page), only collect data for given proposal
    if proposal is not None:
        full_ids = [f for f in full_ids if f[2:7] == proposal]

    # Group files by ID
    file_data = []
    detectors = []
    proposals = []
    for i, file_id in enumerate(full_ids):
        suffixes = []
        count = 0
        for file in filepaths:
            if '_'.join(file.split('/')[-1].split('_')[:-1]) == file_id:
                count += 1

                # Parse filename
                try:
                    file_dict = filename_parser(file)
                except ValueError:
                    # Temporary workaround for noncompliant files in filesystem
                    file_dict = {'activity': file_id[17:19],
                                 'detector': file_id[26:],
                                 'exposure_id': file_id[20:25],
                                 'observation': file_id[7:10],
                                 'parallel_seq_id': file_id[16],
                                 'program_id': file_id[2:7],
                                 'suffix': file.split('/')[-1].split('.')[0].split('_')[-1],
                                 'visit': file_id[10:13],
                                 'visit_group': file_id[14:16]}

                # Determine suffix
                suffix = file_dict['suffix']
                suffixes.append(suffix)

                hdr = fits.getheader(file, ext=0)
                exp_start = hdr['EXPSTART']

        suffixes = list(set(suffixes))

        # Add parameters to sort by
        if file_dict['detector'] not in detectors and \
           not file_dict['detector'].startswith('f'):
            detectors.append(file_dict['detector'])
        if file_dict['program_id'] not in proposals:
            proposals.append(file_dict['program_id'])

        file_dict['exp_start'] = exp_start
        file_dict['suffixes'] = suffixes
        file_dict['file_count'] = count
        file_dict['file_root'] = file_id

        file_data.append(file_dict)
    file_indices = np.arange(len(file_data))

    # Extract information for sorting with dropdown menus
    # (Don't include the proposal as a sorting parameter if the
    # proposal has already been specified)
    if proposal is not None:
        dropdown_menus = {'detector': detectors}
    else:
        dropdown_menus = {'detector': detectors,
                          'proposal': proposals}

    dict_to_render = {'inst': inst,
                      'all_filenames': [os.path.basename(f) for f in filepaths],
                      'tools': MONITORS,
                      'thumbnail_zipped_list': zip(file_indices, file_data),
                      'dropdown_menus': dropdown_menus,
                      'n_fileids': len(file_data),
                      'prop': proposal}

    return dict_to_render
